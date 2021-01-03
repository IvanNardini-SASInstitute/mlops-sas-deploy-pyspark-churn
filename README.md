# Orchestate Spark Analytical enviroment with SAS Workflow Manager


<img src="https://github.com/IvanNardini-SASInstitute/mlops-sas-deploy-pyspark-churn/raw/master/spark_governance.png">


## Covered functionality

This demo is about **orchestrating an E2E analytical model lifecycle of Spark Mlib models using SAS Workflow Manager**

1. Training a Spark Mlib model
2. Import in SAS Model Manager via Viya REST API service
3. Start a HadoopLivy workflow for deploying, scoring, monitoring, and if needed retrain the model in an automated and controlled manner at the same time. 

All this is possible thanks to Model Manager and WorkFlow capabilities.

Below the **high-level architecture of the solution**: 

<img src="https://github.com/IvanNardini-SASInstitute/mlops-sas-deploy-pyspark-churn/master/solution_architecture.png">

## Requirements

An local **Anaconda Spark enviroment** with **sparkmagic** functionalities.

An production **Hadoop-Spark environment** with **Apache Livy server**. Notice: because it's a 

The startup libraries at requirements.txt

To get an **Anaconda Spark enviroment** with **sparkmagic**, please have a look at

1. [Install PySpark to run in Jupyter Notebook on Windows](https://medium.com/@naomi.fridman/install-pyspark-to-run-on-jupyter-notebook-on-windows-4ec2009de21f)
2. [Livy & Jupyter Notebook & Sparkmagic = Powerful & Easy Notebook for Data Scientist](https://blog.chezo.uno/livy-jupyter-notebook-sparkmagic-powerful-easy-notebook-for-data-scientist-a8b72345ea2d)

To get instructions a production **Hadoop-Spark environment** with **Apache Livy server**, please contact [Artem Glazkov](Artem.Glazkov@sas.com)

## Usage 

You can run **SASViya_OSIntgr_SparkMlib_Deployment_final.ipynb** for: 

1. train a LogisticRegression model using Pyspark MLib library
2. register the MetaData of the Model in SAS Model Manager

Once you register the model, assuming that **you set the HadoopLivy workflow**, you start the workflow. Then you claim and complete the task associated to it in a way that you: 

3. Score data in Hadoop-Spark cluster
4. Retrive back the scored data and generate the Perfomance Monitoring charts in SAS Model Manager

And because the demo, we assumed that the model underperforms

5. Retrain the model and register the new version

Below the **HadoopLivy** workflow we build

<img src="https://github.com/IvanNardini/Orchestrate-Spark-in-SAS-Viya/raw/master/2_workflow/workflow.png">

## Contributions

Test it. And please provide us feedback for improvements. Pull requests are welcome as well.

And feel free to reach us at [Ivan Nardini](ivan.nardini@sas.com ), [Artem Glazkov](Artem.Glazkov@sas.com) and [Matteo Landrò](matteo.landro@sas.com) for any clarification
