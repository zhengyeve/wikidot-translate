# Wikidot Site Utilities

A series of command to support wikidot site utilities.
Also support translation (conversion) from simplified Chinese (zh-cn) to traditional chainese (zh-tw) using [OpenCC](https://github.com/BYVoid/OpenCC).


Based on below documentation:
http://developer.wikidot.com/doc:api
http://www.wikidot.com/doc:api

----

## Set up 

If you have multiple python version installed, use a consistent python 3 binary.

### Create Virtual Environment

```shell script
python3 -m venv venv-wikidot
```

### Activate Virtual Environment

```shell script
source venv-wikidot/bin/activate
```

### Install requirement

```shell script
python3 -m pip install -r requirements.txt
```

### Setup credentials


1. Wikidot credentials
Go to `api/` dirctory, copy `credential-wikidot.json.sample` to  `credential-wikidot.json` 
```shell script
cd api/
cp credential-wikidot.json.sample credential-wikidot.json
```

Replace wikidot constant accordingly. 
```JSON
{
    "user":     "WIKIDOT_API_USER",
    "ro_key":   "WIKIDOT_API_KEY_READONLY",
    "rw_key":   "WIKIDOT_API_KEY_READWRITE",
    "site":     "WIKIDOT_SITENAME"
}
```

2. Slack webhook credentials

Goto `api/slack.py` update `WEBHOOK_URL` variable.


### (Optional) Setup conversion exceptions and other constants

You can defiend customized conversion rule using a local JSON file.

Copy `convert_exception.json.example` to `convert_exception.json`
```shell script
cp convert_exception.json.example convert_exception.json
```

In the `convert_exception.json`, update key-value to be the exception of simplified / traditional chainese conversion
```JSON
{
   "UNEXPECTED CONVERTED TOKEN":"EXPECTED TOKEN"
}
```


Update other constants in `apis.consts.py` accordingly for furhter customization. A few options:
- Define image prefix for file related operations.
- Special handles for categories and pages: skip conversion, skip copy, etc



### Run script locally in virtual environment
```shell script
python3 wikidot.py test
```



## Supported commands

Explore more commands in `wikidot.py`

Update one page:
```shell script
python wikidot.py convert_site --page <page_name> [--debug]
```

Update pages within one or multiple category:
```shell script
python wikidot.py convert_site --category <category_name> [<category_name> <category_name>]
```

Update all pages:
```shell script
python wikidot.py convert_site [--debug]
```

Copy file for one page:
```shell script
python wikidot.py copy_files --page <page_name>
```

Copy file for one or multiple category::
```shell script
python wikidot.py copy_files --category <category_name> [<category_name> <category_name>]
```

Copy file for all site:
```shell script
python wikidot.py copy_files
```


## Cloud Deployment and Execution 

### Run script in a docker container
```shell script
docker build -t wikidot . \
&& docker run wikidot python wikidot.py test
```

### Run scirpt in Google Cloud Platform

You can deploy this script to [Google Cloud Run](https://console.cloud.google.com/run) for futher collaboration and automation.


1. Install GCP CLI locally 

https://docs.cloud.google.com/sdk/docs/install-sdk

2. Authentication

https://cloud.google.com/artifact-registry/docs/docker/authentication

```shell script
gcloud auth configure-docker us-central1-docker.pkg.dev,asia-northeast1-docker.pkg.dev
```

3. Setup environment in Google Cloud
Make sure you have a proejct in Google Cloud.
Go to [Artifact](https://console.cloud.google.com/artifacts) and create a repostiory to [host the docker images](https://docs.cloud.google.com/artifact-registry/docs/docker).
Go to [Cloud Run - Services](https://console.cloud.google.com/run/services), [create a service](https://console.cloud.google.com/run/create) using "Deploy a container", select respository created from previous step.



4. Submit image build

Use [Cloud Buld](https://docs.cloud.google.com/artifact-registry/docs/configure-cloud-build#python) to update image build.
```shell script
gcloud builds submit --pack image=CONTAINER_IMAGE_URL
```

5. Setup Cloud Run

In Cloud Run, create jobs based on submitted image.  You can use different script command for different jobs.


### Run script in GitHub Actions

Checkout `.github/workflows` and Github Actions section.
