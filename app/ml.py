import pefile
import pandas as pd
import joblib
import os
import math
import tensorflow.keras.models as models
from urllib.request import urlretrieve
import asyncio

# Use the current script file path to determine the project directory
project_path = os.path.dirname(os.path.abspath(__file__))

rf_model_path = os.path.join(project_path, './src/rf_model.joblib')
nn_model_path = os.path.join(project_path, './src/nn_model.h5')
scaler_path = os.path.join(project_path, './src/scaler.joblib')

# Load the trained ml models
rf_model = joblib.load(rf_model_path)
nn_model = models.load_model(nn_model_path)

# Load the StandardScaler object used to scale the training data
scaler = joblib.load(scaler_path)

# Define a function to extract the required features from the given file
def extract_features(file_url):
    try:
        # Download the file from Firebase Storage
        file_path, _ = urlretrieve(file_url)

        # Get the file size
        file_length = os.path.getsize(file_path)

        # Calculate the entropy of the file
        with open(file_path, 'rb') as f:
            data = bytearray(f.read())
            entropy = 0
            if len(data) > 0:
                # Calculate the frequency of each byte value
                freq_list = []
                for i in range(256):
                    freq_list.append(float(data.count(i))/len(data))
                # Calculate the entropy of the file
                for freq in freq_list:
                    if freq > 0:
                        entropy += -freq * math.log(freq, 2)

        # Extract other features from the file
        pe = pefile.PE(file_path)
        features = {
            'machine_type': pe.FILE_HEADER.Machine,
            'number_of_sections': pe.FILE_HEADER.NumberOfSections,
            'timestamp': pe.FILE_HEADER.TimeDateStamp,
            'pointer_to_symbol_table': pe.FILE_HEADER.PointerToSymbolTable,
            'number_of_symbols': pe.FILE_HEADER.NumberOfSymbols,
            'size_of_optional_header': pe.FILE_HEADER.SizeOfOptionalHeader,
            'characteristics': pe.FILE_HEADER.Characteristics,
            'iat_rva': pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IAT']].VirtualAddress,
            'major_version': pe.OPTIONAL_HEADER.MajorLinkerVersion,
            'minor_version': pe.OPTIONAL_HEADER.MinorLinkerVersion,
            'check_sum': pe.OPTIONAL_HEADER.CheckSum,
            'compile_date': pe.FILE_HEADER.TimeDateStamp,
            'datadir_IMAGE_DIRECTORY_ENTRY_BASERELOC_size': pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_BASERELOC']].Size,
            'datadir_IMAGE_DIRECTORY_ENTRY_EXPORT_size': pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']].Size,
            'datadir_IMAGE_DIRECTORY_ENTRY_IAT_size': pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IAT']].Size,
            'datadir_IMAGE_DIRECTORY_ENTRY_IMPORT_size': pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']].Size,
            'debug_size': pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DEBUG']].Size,
            'export_size': pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']].Size,
            'size_of_code': pe.OPTIONAL_HEADER.SizeOfCode,
            'size_of_initialized_data': pe.OPTIONAL_HEADER.SizeOfInitializedData,
            'size_of_uninitialized_data': pe.OPTIONAL_HEADER.SizeOfUninitializedData,
            'size_of_image': pe.OPTIONAL_HEADER.SizeOfImage,
            'size_of_headers': pe.OPTIONAL_HEADER.SizeOfHeaders,
            'subsystem': pe.OPTIONAL_HEADER.Subsystem,
            'major_operating_system_version': pe.OPTIONAL_HEADER.MajorOperatingSystemVersion,
            'minor_operating_system_version': pe.OPTIONAL_HEADER.MinorOperatingSystemVersion,
            'number_of_rva_and_sizes': pe.OPTIONAL_HEADER.NumberOfRvaAndSizes,
            'base_of_code': pe.OPTIONAL_HEADER.BaseOfCode,
            'entry_point_rva': pe.OPTIONAL_HEADER.AddressOfEntryPoint,
            'resource_size': pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']].Size,
            'size_of_heap_commit': pe.OPTIONAL_HEADER.SizeOfHeapCommit,
            'size_of_heap_reserve': pe.OPTIONAL_HEADER.SizeOfHeapReserve,
            'size_of_stack_commit': pe.OPTIONAL_HEADER.SizeOfStackCommit,
            'size_of_stack_reserve': pe.OPTIONAL_HEADER.SizeOfStackReserve,
            'status': pe.OPTIONAL_HEADER.DllCharacteristics,
            'file_length': file_length,
            'entropy': entropy,
        }
        return pd.DataFrame(features, index=[0])
    except Exception as e:
        print(f"Error while processing file: {file_path}")
        print(f"Error message: {str(e)}")
        return None


# Define the Predic funtion for NN Model
def predic_nn_model_fn(model, input_data):
    return model(input_data)


async def classify_file(file):
    # Extract features from the file
    file_features = extract_features(file)
    if file_features is not None:
        # Scale the features using the same StandardScaler object used to scale the training data
        scaled_features = scaler.transform(file_features.values)

        # Make predictions using the trained model - RF Model
        rf_prediction = rf_model.predict(scaled_features)
        proba = rf_model.predict_proba(scaled_features)

        # Make predictions using the trained model - NN Model
        nn_prediction = predic_nn_model_fn(nn_model, scaled_features)[0]

        # Add prediction values to variables
        rf_pred_value = proba[0][1]
        nn_pred_value = nn_prediction[0]

        if rf_prediction[0] == 1 and proba[0][1] >= 0.85:
            if nn_prediction[0] >= 0.7:
                return {
                    "prediction": "Malware",
                    "rf_probability": f"{rf_pred_value*100:.2f}%",
                    "nn_prediction": f"{nn_pred_value*100:.2f}%"
                }
            else:
                return {
                    "prediction": "Uncertain (mostly Malware)",
                    "rf_probability": f"{rf_pred_value*100:.2f}%",
                    "nn_prediction": f"{nn_pred_value*100:.2f}%"
                }
        else:
            if nn_prediction[0] >= 0.95 and proba[0][1] >= 0.75:
                return {
                    "prediction": "Uncertain (mostly Malware)",
                    "rf_probability": f"{rf_pred_value*100:.2f}%",
                    "nn_prediction": f"{nn_pred_value*100:.2f}%"
                }
            else:
                return {
                    "prediction": "Legitimate",
                    "rf_probability": f"{rf_pred_value*100:.2f}%",
                    "nn_prediction": f"{nn_pred_value*100:.2f}%"
                }
    else:
        return {
            "prediction": "Error occurred while processing the file",
            "rf_probability": "N/A",
            "nn_prediction": "N/A"
        }
