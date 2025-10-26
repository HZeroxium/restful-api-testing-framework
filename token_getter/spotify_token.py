import base64
import requests

# def get_spotify_token():
#     client_id = "de4f6869193d418597a201812475e05f"
#     client_secret = "eaf8382b16df4a899618470521e5f1e3"

#     # Encode client id and secret
#     auth_str = f"{client_id}:{client_secret}"
#     b64_auth_str = base64.b64encode(auth_str.encode()).decode()

#     headers = {
#         "Authorization": f"Basic {b64_auth_str}",
#         "Content-Type": "application/x-www-form-urlencoded"
#     }
#     data = {"grant_type": "client_credentials"}

#     response = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)

#     if response.status_code == 200:
#         token = response.json().get("access_token")
#         print("Access token:", token)
#         return token
#     else:
#         print("Failed to get token:", response.status_code, response.text)
#         return None


# # Example usage
# if __name__ == "__main__":
#     get_spotify_token()


import requests

def get_track_with_token(track_id: str, access_token: str):
    url = f"https://api.spotify.com/v1/tracks/{track_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code == 200:
        data = r.json()
        print("OK:", data["name"], "—", data["artists"][0]["name"])
        return data
    else:
        print("Fail:", r.status_code, r.text)
        return None

# Example: replace with your token and a real track ID
token = "BQCxj0oCPMwY3vZ9jRBqCAjTWoJ39xWOU7kQyn-q2OSufiBF7JbZ5hQXXbwAUD7hKAr7nRS3OQnmBaInSoczdQ_BdpNiF1XRQZGGRIbFtKbL0zJiLtwt9YBaWuogswq4_678DFmw3m4"
get_track_with_token("11dFghVXANMlKmJXsNCbNl", token)
