#!/bin/bash
# 用法: ./scripts/start.sh [i/v/t] [数据路径] [标签路径]
# 示例: ./scripts/start.sh i ./exp_result ./label
data_type="i"
data_dir="./exp_result"
label_dir="./label"
port="10081"

python app.py $data_type $data_dir $label_dir $port
