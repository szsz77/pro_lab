
import json


def save_in_json(save_dict, save_file):
    with open(save_file, 'w') as fp:
        json.dump(save_dict, fp)


def load_from_json(json_file):
    with open(json_file, 'r') as fp:
        return json.load(fp)


def read_txt_file(path):

    with open(path, 'r') as f:
        data = f.readlines()

    return ' '.join(data)