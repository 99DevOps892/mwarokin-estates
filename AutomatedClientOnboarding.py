import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LinearRegression
from scipy.stats import norm
import random

# Sample data for AI-driven onboarding
clients_data = {
    'client_id': [1, 2, 3, 4, 5],
    'location': ['New York', 'London', 'Sydney', 'San Francisco', 'Berlin'],
    'organization_type': ['Tech', 'Finance', 'Retail', 'Tech', 'Health'],
    'individual_name': ['Alice', 'Bob', 'Charlie', 'David', 'Emma'],
    'individual_age': [25, 40, 60, 30, 45],
    'market_segment': ['Software', 'Banking', 'Retail', 'Software', 'Healthcare'],
    'preferred_app': ['Slack', 'Zoom', 'Shopify', 'Asana', 'MedApp'],
    'recommended_app': ['Trello', 'Salesforce', 'BigCommerce', 'Jira', 'HealthSuite'],
    'ecosystem_thinking': ['Collaborative', 'Data-driven', 'Consumer-focused', 'Agile', 'Integrated'],
}

# Convert to DataFrame
clients_df = pd.DataFrame(clients_data)

# Encode categorical data
encoder = LabelEncoder()
clients_df['market_segment_encoded'] = encoder.fit_transform(clients_df['market_segment'])
clients_df['organization_type_encoded'] = encoder.fit_transform(clients_df['organization_type'])

# Function to predict preferred app using regression
def predict_preferred_app(client_id, df):
    regression_model = LinearRegression()
    X = df[['market_segment_encoded', 'organization_type_encoded']]
    y = df['preferred_app'].astype('category').cat.codes  # Convert categories to numerical values
    regression_model.fit(X, y)
    
    client_row = df[df['client_id'] == client_id]
    if client_row.empty:
        return "Client not found"
    
    prediction_code = regression_model.predict(client_row[['market_segment_encoded', 'organization_type_encoded']])
    predicted_app = df['preferred_app'].astype('category').cat.categories[int(prediction_code[0])]
    return f"Predicted Preferred App for Client {client_id}: {predicted_app}"

# Function to perform Monte Carlo simulation for risk analysis
def monte_carlo_simulation():
    trials = 10000
    projected_revenue = []
    for _ in range(trials):
        revenue = np.random.normal(loc=50000, scale=10000)  # Simulating revenue fluctuations
        projected_revenue.append(revenue)
    
    return f"Projected Revenue Range (95% confidence): {np.percentile(projected_revenue, [2.5, 97.5])}"

# AI-driven automation function
def ai_automation(client_id, df):
    scaler = StandardScaler()
    numerical_features = df[['individual_age', 'market_segment_encoded', 'organization_type_encoded']]
    normalized_data = scaler.fit_transform(numerical_features)
    
    kmeans = KMeans(n_clusters=2, n_init=10, random_state=42)
    df['cluster'] = kmeans.fit_predict(normalized_data)
    
    client_cluster = df.loc[df['client_id'] == client_id, 'cluster'].values[0]
    similar_clients = df[df['cluster'] == client_cluster]
    
    return similar_clients[['client_id', 'individual_name', 'market_segment', 'recommended_app']]

# Function to run client onboarding
def client_onboarding(client_id, df):
    print("### AI Client Onboarding ###")
    print(predict_preferred_app(client_id, df))
    print("\nReal-Time Client Segmentation:")
    print(ai_automation(client_id, df))
    print("\nBusiness Intelligence Insights:")
    print(monte_carlo_simulation())

# Run onboarding for a sample client
client_onboarding(1, clients_df)
