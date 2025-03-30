import pandas as pd
from src.utils import load_object

class CustomData:
    def __init__(self, gender, race_ethnicity, parental_level_of_education, lunch, test_preparation_course, reading_score, writing_score):
        self.gender = gender
        self.race_ethnicity = race_ethnicity
        self.parental_level_of_education = parental_level_of_education
        self.lunch = lunch
        self.test_preparation_course = test_preparation_course
        self.reading_score = reading_score
        self.writing_score = writing_score

    def get_data_as_data_frame(self):
        data = {
            'gender': [self.gender],
            'race_ethnicity': [self.race_ethnicity],
            'parental_level_of_education': [self.parental_level_of_education],
            'lunch': [self.lunch],
            'test_preparation_course': [self.test_preparation_course],
            'reading_score': [self.reading_score],
            'writing_score': [self.writing_score]
        }
        return pd.DataFrame(data)

class PredictPipeline:
    def __init__(self):
        self.model = load_object('artifacts/model.pkl')
        self.preprocessor = load_object('artifacts/preprocessor.pkl')

    def predict(self, data):
        data_preprocessed = self.preprocessor.transform(data)
        prediction = self.model.predict(data_preprocessed)
        return prediction


