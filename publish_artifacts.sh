#!/bin/sh
set -e

# Step 1: Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "AWS credentials are missing or invalid."
  exit 1
fi

# Step 2: Upload artifacts
aws s3 cp "$INPUT_PATH" "s3://$INPUT_S3_BUCKET/$INPUT_DESTINATION" --recursive --progress-frequency 30

# Step 3: Publish fileserver URL containing the artifacts
output_file="${GITHUB_OUTPUT}"
echo "url=${INPUT_FILESERVER_URL}/${INPUT_S3_BUCKET}/${INPUT_DESTINATION}" >> ${output_file}
