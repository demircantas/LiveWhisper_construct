import requests

# API endpoint URL
url = 'http://localhost:5000/endpoint'  # Replace with your local endpoint URL

# Sample data to send in the request
data = {
    'name': 'John Doe',
    'email': 'johndoe@example.com'
}

# Send POST request to the local API endpoint
response = requests.post(url, data=data)

# Check the response status code
if response.status_code == 200:
    print('Request successful.')
else:
    print('Request failed.')

# Print the response content
print('Response:', response.text)
