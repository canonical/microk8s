# SWAGGER UI

## Overview

swagger.json holds all the schema and used from Swagger UI to generate the relative pages

It is exposed under the url:

https://127.0.0.1:25000/static/swagger.json

## Maintain swagger schema

Under static folder you can find swagger.yaml 

You can copy paste the contents at editor.swagger.io, do any changes, test the ui, and then export to json file so you can update the swagger.json located under static folder

There is also the option to do it vice-versa; update json file, copy the contents at editor.swagger.io, it will convert it to yaml, and copy the contents under /static/swagger.yaml

## Accessing SwaggerUI

The UI can be accessed from this url:
https://127.0.0.1:25000/swagger
