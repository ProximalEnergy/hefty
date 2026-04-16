#!/bin/sh

set -eu

lambda_task_root="${LAMBDA_TASK_ROOT:?LAMBDA_TASK_ROOT must be set}"
requirements_path="/tmp/requirements.lock.txt"

uv export --project pv-eem --frozen --no-dev --no-editable -o "${requirements_path}"
uv pip install --system -r "${requirements_path}" --target "${lambda_task_root}"

rm -f "${requirements_path}"
