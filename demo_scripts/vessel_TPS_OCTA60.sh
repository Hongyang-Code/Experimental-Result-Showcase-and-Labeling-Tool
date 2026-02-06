#!/bin/bash
# 用法: ./scripts/start.sh [i/v/t] [数据路径] [标签路径]
# 示例: ./scripts/start.sh i ./exp_result ./label
data_type="i"
data_dir="/data2/lhy/project/GeoFormer-main/Visualization/ResultVis/result_tps_vis_768"
label_dir="/data2/lhy/project/GeoFormer-main/Visualization/ResultVis/result_tps_vis_768/label"
port="10008"

python app.py $data_type $data_dir $label_dir $port
