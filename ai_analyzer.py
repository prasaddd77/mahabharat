from groq import Groq
import os
from dotenv import load_dotenv

# load environment variables from .env
load_dotenv()

# Best practice: store key as environment variable
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def analyze_logs(file):

    with open(file, "r") as f:
        logs = f.read()

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": "You are an expert DevOps SRE who analyzes CI/CD pipeline logs and identifies root causes and remediation steps."
            },
            {
                "role": "user",
                "content": f"Analyze these pipeline logs and suggest root cause and remediation:\n\n{logs}"
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content

# def analyze_logs(file):

#     with open(file, "r") as f:
#         logs = f.read()

#     response = ollama.chat(
#         model="llama3",
#         messages=[
#             {
#                 "role": "system",
#                 "content": "You are a DevOps SRE who analyzes CI/CD pipeline logs and suggests root cause and fixes."
#             },
#             {
#                 "role": "user",
#                 "content": f"Analyze these pipeline logs and suggest root cause and remediation:\n{logs}"
#             }
#         ]
#     )

#     return response["message"]["content"]

# from openai import OpenAI
# import certifi
# import os
# import httpx

# # proxy = "http://xv.prasad.ranjane%40singtel.com:Asha%5E%21%40%23%242411pwd@singtelproxy.net.vic:80"

# http_client = httpx.Client(verify=False)

# client = OpenAI(api_key="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", http_client=http_client)  # replace with your key

# def analyze_logs(log_file="pipeline_logs.txt"):

#     with open(log_file, "r") as f:
#         logs = f.read()

#     prompt = f"""
#     You are an expert DevOps SRE.

#     Analyze these CI/CD pipeline logs and provide:

#     1. Root cause
#     2. Failure type
#     3. Suggested fix
#     4. Self-healing automation action

#     Logs:
#     {logs}
#     """

#     response = client.chat.completions.create(
#         model="gpt-4.1-mini",
#         messages=[
#             {"role": "system", "content": "You are an expert Kubernetes and CI/CD SRE."},
#             {"role": "user", "content": prompt}
#         ]
#     )

#     result = response.choices[0].message.content
#     print("\nAI Analysis:\n")
#     print(result)
#     return result

# if __name__ == "__main__":
#     analyze_logs()