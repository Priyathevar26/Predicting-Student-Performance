import dill

def load_object(file_path):
    with open(file_path, 'rb') as file:
        return dill.load(file)
