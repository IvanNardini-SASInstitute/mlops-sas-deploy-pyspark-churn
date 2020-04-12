import requests
import json
import time
import datetime
import sys
import os
import textwrap
import base64
from livy import LivySession

from sasctl import Session
from sasctl.core import get, post, put, delete


LIVY_URL = 'http://cbr02.rus.sas.com:8998'


train_code = textwrap.dedent("""
            
    import pandas as pd

    from pyspark.sql.functions import *
    from pyspark.sql.types import *
    from pyspark.ml.feature import VectorAssembler
    from pyspark.ml.classification import LogisticRegression

    # Loads datatest
    df = spark.read.csv('/tmp/datatoscore.csv', header = True, inferSchema = True)
    
    # Assemble features into one vector for the model
    ignore = ['BAD']
    assembler = VectorAssembler(inputCols=[x for x in df.columns if x not in ignore],
                                outputCol='features')
    df1 = assembler.transform(df)
    dataset = df1.select(col('features'),col('BAD'))
    
    #Train a Logistic model
    lr = LogisticRegression(labelCol = 'BAD', maxIter=10)
    lrModel = lr.fit(dataset)
    
    #Store new model
    lrModel.write().overwrite().save('/tmp/models/logit')      
        
""")


score_code = textwrap.dedent("""
            
    import pandas as pd

    from pyspark.sql.functions import *
    from pyspark.sql.types import *
    from pyspark.ml.feature import VectorAssembler
    from pyspark.ml.classification import LogisticRegressionModel
    from pyspark.ml.evaluation import BinaryClassificationEvaluator

    # Loads dataset to score and prepare data
    
    df = spark.read.csv('/tmp/datatoscore.csv', header = True, inferSchema = True)
    # Assemble features into one vector for the model
    ignore = ['BAD']
    assembler = VectorAssembler(inputCols=[x for x in df.columns if x not in ignore],
                                outputCol='features')
    df1 = assembler.transform(df)
    dataset = df1.select(col('features'),col('BAD'))
    
    # Loads model
    dpmodel = LogisticRegressionModel.load('/tmp/models/logit')
    
    # Make predictions
    prediction = dpmodel.transform(dataset)
    
    #Generate final scored data
    split1_udf = udf(lambda value: value[0].item(), FloatType())
    split2_udf = udf(lambda value: value[1].item(), FloatType())
    probabilities = prediction.\
                    select(split1_udf('probability').alias('P_BAD0'), split2_udf('probability').alias('P_BAD1'))
    df_probabilities=probabilities.toPandas()
    df_abt = pd.read_csv('datatoscore.csv')
    target = df_abt['BAD']
    df_abt.drop(labels=['BAD'], axis=1, inplace = True)
    df_abt.insert(0, 'BAD', target)
    df_scored=pd.concat([df_abt, df_probabilities], axis=1)
    df_scored.to_csv('tmp/datascored.csv',sep=',',index=False)
        
""")


class Core:
    def __init__(self, withLogfile=False, procId = ''):
        os.chdir("/home/sasdemo/Viya_Spark_orchestration/")

        self.withLogfile = withLogfile
        self.startTimestamp = int(time.time())

        self.log("Starting initialization...")

        self.protocol = 'http'
        self.server ='rusretailviya.rus.sas.com'
        self.authUri = '/SASLogon/oauth/token'
        self.user = 'sasdemo'
        self.password ='Orion123'
        self.modelId = '3c3e2fa3-bbd3-4cf7-aa93-834b6c953bb3'

        r = requests.post(
            self.protocol+'://'+ self.server + self.authUri,
            params={
                'grant_type': 'password',
                'username': self.user,
                'password': self.password
            },
            headers = {
                'Authorization': 'Basic %s' % base64.b64encode(b'sas.ec:').decode(encoding='utf8')
            }
        )
        self.token = json.loads(r.text)['access_token']
        self.log("Acquired REST API token!")

        self.session = Session(self.server, self.user, self.password, protocol='http')
        self.wfProcessId = procId
        self.loadModelFileMeta()


    def getWorkflowVar(self, name, getSchema=False):
        headers={
            'Accept-Language': 'en_us'
        }        
        schema = get("/workflow/processes/"+str(self.wfProcessId)+"/variables/"+str(name), headers=headers, raw=True)
        
        if schema.get('value', None) is not None:
            self.log("Successfully got "+str(name)+" = "+str(schema['value'])+".")
        else:
            self.log("Error getting variable "+str(name)+".")
            self.log(schema)

        if getSchema:
            return schema
        
        return schema.get('value', None)


    def setWorkflowVar(self, name, value):
        headers={
            'Accept-Language': 'en_us',
            'Content-Type': 'application/json'
        }
        schema = self.getWorkflowVar(name, getSchema=True)
        for key in ['links', 'localizedName', 'description']:
            if key in schema:
                del schema[key]
        schema['value'] = value

        schema = put("/workflow/processes/"+str(self.wfProcessId)+"/variables/"+str(name), headers=headers, json=schema, raw=True)
        
        if schema.get('value', None) == value:
            self.log("Successfully set "+str(name)+" to "+str(value)+".")
        else:
            self.log("Error setting variable "+str(name)+".")
            self.log(schema)


    def log(self, msg):
        if self.withLogfile:
            out = open("logs/"+str(self.startTimestamp)+"-"+str(self.task)+".log", "a+")
        else:
            out = sys.stdout
        
        print("["+str(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))+"] "+str(msg), file=out)

        if self.withLogfile:
            print("["+str(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))+"] "+str(msg))
            out.close()

    
    def loadModelFileMeta(self):
        headers = {
            'Content-Type': 'application/octet-stream',
            'Authorization': 'Bearer ' + self.token
        }
        url = str(self.protocol)+"://"+str(self.server)+"/modelRepository/models/"+str(self.modelId)+"/contents"
        contents = requests.get(url, headers=headers).json()
        for item in contents['items']:
            # item['role'] == score and 
            if item['name'][-5:] == '.pmml':
                self.modelFilename = item['name']
                self.contentId = item['id']
                break

        self.log("Loaded model file name ("+str(self.modelFilename)+") and content id.")

    
    def createNewVersion(self):
        headers = {
            'Content-Type': 'application/vnd.sas.models.model.version+json',
            'Accept': 'application/vnd.sas.models.model.version+json',
            'Authorization': 'Bearer ' + self.token
        }
        body = '{"option":"major"}'
        url = str(self.protocol)+"://"+str(self.server)+"/modelRepository/models/"+str(self.modelId)+"/modelVersions"

        fileResult = requests.post(url, headers=headers, data=body).json()
        if 'creationTimeStamp' in fileResult:
            self.log("Model version created!")
        else:
            self.log("Error!")
        self.log(fileResult)

    
    def uploadModelFile(self):
        headers={
            'Authorization': 'Bearer ' + self.token
        }
        url = str(self.protocol)+"://"+str(self.server)+"/modelRepository/models/"+str(self.modelId)+"/contents/"+str(self.contentId)
        r = requests.delete(url, headers=headers)
        if r.status_code != 204:
            self.log("Error deleting model.")
        else:
            self.log("Removed old model file.")

        headers={
            'Content-Type': 'application/octet-stream',
            'Authorization': 'Bearer ' + self.token
        }
        url = str(self.protocol)+"://"+str(self.server)+"/modelRepository/models/"+str(self.modelId)+"/contents?name="+str(self.modelFilename)
        with open(self.modelFilename, 'rb') as pklFile:
            r = requests.post(url, data=pklFile, headers=headers)

        fileResult = r.json()
        if 'creationTimeStamp' in fileResult:
            self.log("Uploaded model file to server.")
        else:
            self.log("Error!")
        self.log(fileResult)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Not enough arguments! Usage: python "+str(sys.argv[0])+" <command>")
        exit()
    else:
        core = Core()
        if sys.argv[1] == 'train':
            with LivySession(LIVY_URL) as session:
                session.run(train_code)
            os.system('scp sasdemo@cbr02.rus.sas.com:/tmp/models/logit sasdemo@rusretailviya.rus.sas.com:/home/sasdemo/Viya_Spark_orchestration/')
            core.createNewVersion()
            core.uploadModelFile()
        elif sys.argv[1] == 'score':
            with LivySession(LIVY_URL) as session:
                session.run(score_code)        
