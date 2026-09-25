import os
import pandas as pd
import numpy as np
import joblib
import shutil
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(os.path.dirname(BASE_DIR), 'diabetes_prediction', 'dataset')
DATASET_PATH = os.path.join(DATASET_DIR, 'diabetes.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'diabetes_model.pkl')
SCALER_PATH = os.path.join(BASE_DIR, 'scaler.pkl')

# User's specific path
USER_DATASET_PATH = r"C:\Users\USER\OneDrive\Documents\diabetes_prediction\diabetes.csv"


def ensure_dataset():
    """Ensure diabetes dataset exists from user path or local workspace."""
    if os.path.exists(USER_DATASET_PATH):
        print(f"Reading user dataset from: {USER_DATASET_PATH}")
        os.makedirs(DATASET_DIR, exist_ok=True)
        shutil.copy(USER_DATASET_PATH, DATASET_PATH)
        return USER_DATASET_PATH

    if os.path.exists(DATASET_PATH):
        print(f"Dataset found at: {DATASET_PATH}")
        return DATASET_PATH

    alt_path = os.path.join(BASE_DIR, 'diabetes.csv')
    if os.path.exists(alt_path):
        print(f"Dataset found at: {alt_path}")
        return alt_path

    print("Dataset not found. Generating initial benchmark dataset...")
    os.makedirs(DATASET_DIR, exist_ok=True)

    np.random.seed(42)
    n_samples = 800

    pregnancies = np.random.randint(0, 15, n_samples)
    glucose = np.random.normal(120, 30, n_samples).clip(70, 200)
    blood_pressure = np.random.normal(70, 12, n_samples).clip(40, 122)
    skin_thickness = np.random.normal(20, 10, n_samples).clip(0, 99)
    insulin = np.random.normal(80, 50, n_samples).clip(0, 846)
    bmi = np.random.normal(32, 7, n_samples).clip(18, 67)
    pedigree = np.random.exponential(0.4, n_samples).clip(0.08, 2.42)
    age = np.random.randint(21, 81, n_samples)

    # Calculate realistic outcome logit based on clinical risk factors
    logit = (
        0.04 * (glucose - 100) +
        0.05 * (bmi - 25) +
        0.03 * (age - 30) +
        1.2 * pedigree +
        0.08 * pregnancies +
        0.01 * (blood_pressure - 70) +
        0.002 * insulin -
        4.0
    )
    prob = 1 / (1 + np.exp(-logit))
    outcome = (prob > 0.5).astype(int)

    df = pd.DataFrame({
        'Pregnancies': pregnancies,
        'Glucose': np.round(glucose, 1),
        'BloodPressure': np.round(blood_pressure, 1),
        'SkinThickness': np.round(skin_thickness, 1),
        'Insulin': np.round(insulin, 1),
        'BMI': np.round(bmi, 1),
        'DiabetesPedigreeFunction': np.round(pedigree, 3),
        'Age': age,
        'Outcome': outcome
    })

    df.to_csv(DATASET_PATH, index=False)
    print(f"Benchmark dataset saved successfully to: {DATASET_PATH}")
    return DATASET_PATH


def load_and_preprocess_data(file_path):
    """Load and preprocess diabetes dataset."""
    df = pd.read_csv(file_path)
    print(f"\nDataset Overview:\nShape: {df.shape}")
    print(df.head())

    # Replace 0 values with NaN for biometric indicators where 0 means missing
    zero_cols = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']
    for col in zero_cols:
        if col in df.columns:
            df[col] = df[col].replace(0, np.nan)
            df[col] = df[col].fillna(df[col].median())

    feature_cols = ['Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI',
                    'DiabetesPedigreeFunction', 'Age']
    X = df[feature_cols]
    y = df['Outcome']

    return X, y, feature_cols


def train_and_evaluate():
    """Train multiple ML models, select best model, and save model and scaler."""
    dataset_file = ensure_dataset()
    X, y, feature_cols = load_and_preprocess_data(dataset_file)

    # Train / Test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Feature Scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    models = {
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'Gradient Boosting': GradientBoostingClassifier(random_state=42),
        'Logistic Regression': LogisticRegression(random_state=42),
        'Support Vector Machine': SVC(probability=True, random_state=42),
        'Decision Tree': DecisionTreeClassifier(random_state=42),
        'K-Nearest Neighbors': KNeighborsClassifier()
    }

    best_model = None
    best_accuracy = 0.0
    best_model_name = ""

    print("\n" + "=" * 50)
    print(" MODEL TRAINING AND EVALUATION ")
    print("=" * 50)

    for name, model in models.items():
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)
        acc = accuracy_score(y_test, y_pred)
        print(f"Model: {name:<25} | Accuracy: {acc * 100:.2f}%")

        if acc > best_accuracy:
            best_accuracy = acc
            best_model = model
            best_model_name = name

    print("\n" + "=" * 50)
    print(f"BEST MODEL: {best_model_name} with Accuracy: {best_accuracy * 100:.2f}%")
    print("=" * 50)

    # Detailed classification report for best model
    y_pred_best = best_model.predict(X_test_scaled)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred_best))

    # Save Model & Scaler
    joblib.dump(best_model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(feature_cols, os.path.join(BASE_DIR, 'feature_names.pkl'))

    print(f"\nBest model saved to: {MODEL_PATH}")
    print(f"Scaler saved to: {SCALER_PATH}")
    return best_model, scaler, feature_cols


def predict_single_sample(features_dict):
    """Predict diabetes risk probability for a single input record."""
    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        print("Model files not found. Training model first...")
        train_and_evaluate()

    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    feature_cols = joblib.load(os.path.join(BASE_DIR, 'feature_names.pkl'))

    # Support multiple key formats with normal defaults
    pregnancies = features_dict.get('Pregnancies', features_dict.get('pregnancies', 0))
    glucose = features_dict.get('Glucose', features_dict.get('glucose', 90))
    bp = features_dict.get('BloodPressure', features_dict.get('blood_pressure', 75))
    systolic_bp = features_dict.get('systolic_bp', features_dict.get('SystolicBP', features_dict.get('systolic', 115)))
    diastolic_bp = features_dict.get('diastolic_bp', features_dict.get('DiastolicBP', features_dict.get('diastolic', bp)))
    skin = features_dict.get('SkinThickness', features_dict.get('skin_thickness', 20))
    insulin = features_dict.get('Insulin', features_dict.get('insulin', 10))
    bmi = features_dict.get('BMI', features_dict.get('bmi', 22.0))
    pedigree = features_dict.get('DiabetesPedigreeFunction', features_dict.get('pedigree', features_dict.get('diabetes_pedigree', 0.35)))
    age = features_dict.get('Age', features_dict.get('age', 25))

    try:
        pregnancies = float(pregnancies or 0)
        glucose = float(glucose or 90)
        bp = float(bp or 75)
        systolic_bp = float(systolic_bp or 115)
        diastolic_bp = float(diastolic_bp or bp or 75)
        skin = float(skin or 20)
        insulin = float(insulin or 10)
        bmi = float(bmi or 22.0)
        pedigree = float(pedigree or 0.35)
        age = float(age or 25)
    except ValueError:
        pregnancies, glucose, bp, systolic_bp, diastolic_bp, skin, insulin, bmi, pedigree, age = 0, 90, 75, 115, 75, 20, 10, 22.0, 0.35, 25

    # Machine Learning prediction
    input_data = [pregnancies, glucose, diastolic_bp, skin, insulin, bmi, pedigree, age]
    df_single = pd.DataFrame([input_data], columns=feature_cols)
    scaled_data = scaler.transform(df_single)

    prob = model.predict_proba(scaled_data)[0][1]
    prediction = int(model.predict(scaled_data)[0])

    # Calculate clinical risk score (starts at 0.0 for completely normal parameters)
    clinical_score = 0.0

    # 1. Glucose Impact (ADA Criteria: <100 Normal [0], 100-125 Prediabetes [+20], 126-199 Diabetes [+45], >=200 Markedly Elevated [+70])
    if glucose >= 200:
        clinical_score += 70
    elif glucose >= 126:
        clinical_score += 45
    elif glucose >= 100:
        clinical_score += 20

    # 2. Blood Pressure Impact (AHA Criteria: <120/<80 Normal [0], 120-129/<80 Elevated [+15], 130-139 or 80-89 Stage 1 [+30], >=140 or >=90 Stage 2 [+50])
    if systolic_bp >= 140 or diastolic_bp >= 90:
        clinical_score += 50
    elif (130 <= systolic_bp <= 139) or (80 <= diastolic_bp <= 89):
        clinical_score += 30
    elif (120 <= systolic_bp <= 129) and diastolic_bp < 80:
        clinical_score += 15

    # 3. Fasting Insulin Impact (<3 Low [0], 3-10 Normal [0], >10-25 Elevated [+15], >25 High [+35])
    if insulin > 25:
        clinical_score += 35
    elif insulin > 10:
        clinical_score += 15

    # 4. Body Mass Index (BMI) Impact (<25 Normal [0], 25-29.9 Overweight [+12], 30-34.9 Obese [+25], >=35 Severe Obese [+40])
    if bmi >= 35:
        clinical_score += 40
    elif bmi >= 30:
        clinical_score += 25
    elif bmi >= 25:
        clinical_score += 12

    # 5. Pedigree, Age, Pregnancies, Skin Thickness
    if pedigree >= 0.8:
        clinical_score += 15
    elif pedigree >= 0.5:
        clinical_score += 8

    if skin > 30:
        clinical_score += 5

    if pregnancies >= 4:
        clinical_score += 8
    elif pregnancies >= 2:
        clinical_score += 4

    if age >= 45:
        clinical_score += 10
    elif age >= 35:
        clinical_score += 5

    # Combine ML probability (50%) with Clinical risk score (50%)
    ml_pct = prob * 100
    combined_score = (ml_pct * 0.5) + (clinical_score * 0.5)
    final_risk_score = round(min(98.5, max(5.0, combined_score)), 1)

    # Threshold Overrides for Severe Medical Conditions
    if glucose >= 200 or (systolic_bp >= 160 or diastolic_bp >= 100):
        final_risk_score = max(final_risk_score, 70.0)
    elif glucose >= 126:
        final_risk_score = max(final_risk_score, 45.0)

    # User Specified Risk Thresholds:
    # Below 40% -> Low Risk
    # 40% - 65% -> Moderate Risk
    # After 65% -> High Risk
    if final_risk_score > 65.0:
        risk_level = "High Risk"
    elif final_risk_score >= 40.0:
        risk_level = "Moderate Risk"
    else:
        risk_level = "Low Risk"

    return {
        'prediction': prediction,
        'probability': round(float(prob), 4),
        'risk_score': final_risk_score,
        'risk_level': risk_level
    }


if __name__ == '__main__':
    train_and_evaluate()