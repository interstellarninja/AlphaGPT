from pydantic import BaseModel
from typing import List, Dict
from schema import OutputSchema
import yaml 

class PromptSchema(BaseModel):
    Human: str
    Objective: str
    Guidelines: str
    Documents: str
    Examples: str
    Instructions: str 
    Schema: str
    Assistant: str

class PromptManager:
    def format_yaml_prompt(self, prompt_schema: PromptSchema, variables: Dict) -> str:
        formatted_prompt = ""
        for field, value in prompt_schema.dict().items():
            formatted_value = value.format(**variables)
            formatted_prompt += f"{field}:\n{formatted_value}\n"
        return formatted_prompt

    def read_yaml_file(self, file_path: str) -> PromptSchema:
        with open(file_path, 'r') as file:
            yaml_content = yaml.safe_load(file)

        prompt_schema = PromptSchema(
            Human=yaml_content.get('Human', ''),
            Objective=yaml_content.get('Objective', ''),
            Guidelines=yaml_content.get('Guidelines', ''),
            Documents=yaml_content.get('Documents', ''),
            Examples=yaml_content.get('Examples', ''),
            Instructions=yaml_content.get('Output_instructions', ''),
            Schema=yaml_content.get('Output_schema', ''),
            Assistant=yaml_content.get('Assistant', '')
        )
        return prompt_schema
    
    def generate_prompt(self, file_path, variables):
        prompt_schema = self.read_yaml_file(file_path)

        prompt = self.format_yaml_prompt(prompt_schema, variables)

        return prompt

# Example usage:
if __name__ == "__main__":
    # Create an instance of PromptManager
    prompt_manager = PromptManager()

    # Read the YAML file and get the prompt schema
    yaml_file_path = "./prompt_assets/prompt.yaml"
    
    # Set variables for YAML
    variables = {
        "ticker": "NVDA",
        "company": "Nvidia",
        "query": "Nvidia (NVDA) stock performance",
        "doc_list": "document list",
        "few_shot_examples": "examples list",
        "pydantic_schema": OutputSchema.schema(),
    }
    prompt_schema = prompt_manager.read_yaml_file(yaml_file_path)

    # Format the YAML prompt
    formatted_prompt = prompt_manager.format_yaml_prompt(prompt_schema, variables)

    # Print the formatted prompt
    print(formatted_prompt)