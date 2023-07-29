from agentmemory import create_memory
from easycompletion import (
    compose_prompt,
    compose_function,
)
from tinyagi.utils import log

from tinyagi.context.knowledge import add_knowledge

from easycompletion import openai_function_call


def compose_orient_prompt(context):
    """
    This function formats the orientation prompt by inserting the context data into a pre-defined template.

    Args:
        context (dict): The dictionary containing data about the current state of the system, such as current epoch, time, date, recent knowledge, and events.

    Returns:
        str: The fully formed orientation prompt with the data filled in from the context.
    """
    return compose_prompt(
        """\
Current Epoch: {{epoch}}
The current time is {{current_time}} on {{current_date}}.
{{recent_knowledge}}
{{events}}
# Assistant Task
- Summarize what happened in Epoch {{last_epoch}} and reason about what I should do next to move forward.
- First, summarize as yourself (the assistant). Include any relevant information for me, the user, for the next step.
- Next summarize as if you were me, the user, in the first person from my perspective. Use "I" instead of "You".
- Lastly, include any new knowledge that I learned this epoch as an array of knowledge items.
- Your summary should include what I learned, what you think I should do next and why. You should argue for why you think this is the best next step.
- I am worried about getting stuck in a loop or make new progress. Your reasoning should be novel and interesting and helpful me to make progress towards my goals.
- Each knowledge array item should be a factual statement that I learned, and should include the source, the content and the relationship.
- For the "content" of each knowledge item, please be extremely detailed. Include as much information as possible, including who or where you learned it from, what it means, how it relates to my goals, etc.
- ONLY extract knowledge from the last epoch, which is #{{last_epoch}}. Do not extract knowledge from previous epochs.
- If there is no new knowledge, respond with an empty array [].\
""",
        context,
    )


def compose_orient_function():
    """
    This function defines the structure and requirements of the 'orient' function to be called in the 'orient' stage of the OODA loop.

    Returns:
        dict: A dictionary containing the details of the 'orient' function, such as its properties, description, and required properties.
    """
    return compose_function(
        "summarize_recent_events",
        properties={
            "summary_as_assistant": {
                "type": "string",
                "description": "Respond to the me, the user, as yourself, the assistant. Summarize what has happened recently, what you learned from it and what you'd like to do next. Use 'You' instead of 'I'.",
            },
            "summary_as_user": {
                "type": "string",
                "description": "Resphrase your response as if you were me, the user, from the user's perspective in the first person. Use 'I' instead of 'You'.",
            },
            "knowledge": {
                "type": "array",
                "description": "An array of knowledge items that are extracted from my last epoch of events and the summary of those events. Only include knowledge that has not been learned before. Knowledge can be about anything that would help me. If none, use an empty array.",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Where did I learn this? From a connector, the internet, a user or from my own reasoning? Use first person, e.g. 'I learned this from the internet.', from the user's perspective",
                        },
                        "content": {
                            "type": "string",
                            "description": "The actual knowledge I learned. Please format it as a sentence, e.g. 'The sky is blue.' from the user's perspective, in the first person, e.g. 'I can write shell scripts by running a shell command, calling cat and piping out.'",
                        },
                        "relationship": {
                            "type": "string",
                            "description": "What is useful, interesting or important about this information to me and my goals? How does it relate to what I'm doing? Use first person, e.g. 'I can use X to do Y.' from the user's perspective",
                        },
                    },
                },
            },
        },
        description="Summarize the most recent events and decide what to do next.",
        required_properties=["summary_as_assistant", "summary_as_user", "knowledge"],
    )


def orient(context):
    """
    This function serves as the 'Orient' stage in the OODA loop. It uses the current context data to summarize the previous epoch and formulate a plan for the next steps.

    Args:
        context (dict): The dictionary containing data about the current state of the system.

    Returns:
        dict: The updated context dictionary after the 'Orient' stage, including the summary of the last epoch, relevant knowledge, available actions, and so on.
    """
    context["last_epoch"] = context["epoch"]
    context["epoch"] = context["epoch"] + 1

    response = openai_function_call(
        text=compose_orient_prompt(context), functions=compose_orient_function()
    )

    arguments = response["arguments"]
    if arguments is None:
        arguments = {}
        print("No arguments returned from orient_function")

    new_knowledge = []

    # Create new knowledge and add to the knowledge base
    knowledge = arguments.get("knowledge", [])
    if len(knowledge) > 0:
        for k in knowledge:
            # each item in knowledge contains content, source and relationship
            metadata = {
                "source": k["source"],
                "relationship": k.get("relationship", None),
                "epoch": context["epoch"],
            }

            add_knowledge(k["content"], metadata=metadata)
            new_knowledge.append(k["content"])

    # Get the summary and add to the context object
    summary = response["arguments"]["summary_as_user"]
    summary_header = "Summary of Last Epoch:"

    log_content = ""

    if summary is "" or summary is None:
        context["summary"] = None
    else:
        context["summary"] = summary_header + "\n" + summary + "\n"
        log_content += context["summary"]

    if len(new_knowledge) > 0:
        log_content += "\nNew Knowledge:\n" + "\n".join(new_knowledge)
    
    if len(log_content) > 0:
        log(log_content, source="orient", type="step", title="tinyagi")

    # Add context summary to event stream
    create_memory(
        "events", summary, metadata={"type": "summary", "epoch": context["epoch"]}
    )

    return context
