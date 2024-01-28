# Lambda Video Converter
Standardizes and converts a video uploaded to an S3 bucket to an S3 bucket using lambda function and FFMPEG library


## How to deploy

1. Deploying ffmpeg layer

`aws lambda publish-layer-version --layer-name ffmpeg-layer --zip-file fileb://layers/ffmpeg-lambda-layer.zip --compatible-runtimes python3.8 --region us-east-1`

Layer directory tree (if you want to use the latest ffmpeg version, follow the directory structure bellow)

├── layers
│   └── ffmpeg-lambda-layer.zip
│       ├── bin
│       │   └── ffmpeg (the ffmpeg binaries must be extracted here)


2. Deploying serverless stack

`$> serverless deploy`

3. Testing

- Upload a .mp4 file to YOUR_BUCKET_NAME/upload/ directory
- After processing you will find the output in YOUR_BUCKET_NAME/videos/ directory