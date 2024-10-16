import os
import json
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Literal, List


class Action(BaseModel):
    action: Literal['left', 'right', 'up', 'down', 'pickup', 'drop'] = Field(
        ..., title="Action", description="The action to perform."
    )
    reason: str = Field(
        ..., title="Reason", description="The reason for the action."
    )

class Plan(BaseModel):
    instructions: List[Action] = Field(
        ..., title="Instructions", description="The list of instructions."
    )

prompt_template_paths = {
    "system": "prompts/system.txt",
    "plan": "prompts/plan.txt",
}


class LLMEngine:

    def __init__(self, llm_provider: str, llm_name: str, temperature: float):
        self.llm_provider = llm_provider
        self.llm_name = llm_name
        self.temperature = temperature

    def generate_plan(self, agent_observations, user_instructions):

        # Load the system prompt template.
        system_prompt_template = PromptTemplate.from_file(prompt_template_paths["system"])
        system_prompt = system_prompt_template.format()

        # Load the work prompt template.
        work_prompt_template = PromptTemplate.from_file(prompt_template_paths["plan"])
        work_prompt = work_prompt_template.format(
            agent_observations=json.dumps(agent_observations, indent=2),
            user_instructions=user_instructions
        )

        # Parse the instructions.
        pydantic_parser = PydanticOutputParser(pydantic_object=Plan)
        
        format_instructions = pydantic_parser.get_format_instructions()
        work_prompt += "\n\n" + format_instructions

        messages = [
            ("system", system_prompt),
            ("user", work_prompt),
        ]

        # Get the model and invoke it.
        llm = self.__get_model(self.llm_provider, self.llm_name, temperature=self.temperature)
        response = llm.invoke(messages)
        messages += [("assistant", response)]
        self.__log_messages(messages)
        plan = pydantic_parser.invoke(response)


        # Print the plan as a JSON string.
        data = plan.model_dump_json()
        data = json.loads(data)
        print(json.dumps(data, indent=2))


        return plan
    

    def __log_messages(self, messages):

        messages_path = "output/messages.md"

        # Append the messages to the file.
        with open(messages_path, "a") as file:

            # Add the timestamp.
            file.write(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            for role, message in messages:
                file.write(f"## {role.upper()}\n\n{message}\n\n")


    def __get_model(self, model_provider, model_name, temperature=0.5):
        """
        Get a model.
        :param model_provider: The model provider.
        :param model_name: The model name.
        :param temperature: The temperature.
        :return: The model.
        """

        assert isinstance(model_provider, str)
        assert isinstance(model_name, str)

        def raise_if_not_set(environment_variables):
            for env_var in environment_variables:
                if env_var not in os.environ:
                    raise ValueError(f"{env_var} environment variable is not set.")

        if model_provider == "openai":
            raise_if_not_set(["OPENAI_API_KEY"])
            return ChatOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name=model_name,
                temperature=temperature,
            )
        elif model_provider == "ollama":
            return ChatOpenAI(
                base_url="http://localhost:11434/v1" if "OLLAMA_OPENAI_BASE" not in os.environ else os.getenv("OLLAMA_OPENAI_BASE"),
                api_key="ollama",
                model_name=model_name,
                temperature=temperature,
            )
        elif model_provider == "anthropic":
            raise_if_not_set(["ANTHROPIC_API_KEY"])
            return ChatAnthropic(
                model=model_name,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                temperature=temperature,
                max_tokens=8192,
            )
        else:
            raise ValueError(f"Model provider {model_provider} not supported.")
