import os
from google import genai
from google.genai import types

# Reads your GEMINI_API_KEY environment variable
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Function/Tool declarations for Gemini
tools = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="open_app",
                description="Launches an app and drags its window into view.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "app_name": types.Schema(
                            type=types.Type.STRING, 
                            description="Executable or system command (e.g., notepad, calc, chrome, mspaint)"
                        ),
                        "window_title": types.Schema(
                            type=types.Type.STRING, 
                            description="Partial window title to locate (e.g., Notepad, Calculator, Chrome)"
                        )
                    },
                    required=["app_name", "window_title"]
                ),
            ),
            types.FunctionDeclaration(
                name="search_web",
                description="Searches Google for the user.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING, 
                            description="The query string to search on Google"
                        )
                    },
                    required=["query"]
                ),
            ),
            types.FunctionDeclaration(
                name="run_powershell",
                description="Runs a PowerShell (.ps1) script located on the user's Desktop.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "script_name": types.Schema(
                            type=types.Type.STRING, 
                            description="Name of the .ps1 file on Desktop (e.g., backup.ps1, script)"
                        )
                    },
                    required=["script_name"]
                ),
            ),
        ]
    )
]

def parse_user_command(prompt: str):
    """Processes natural language prompts into executable actions."""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=tools,
                temperature=0.0
            )
        )
        
        if response.function_calls:
            call = response.function_calls[0]
            return {"action": call.name, "args": call.args}
        return {"action": "talk", "reply": response.text}
    except Exception as e:
        print(f"AI parsing error: {e}")
        return {"action": "none", "args": {}}