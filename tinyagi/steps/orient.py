from agentmemory import create_event
from easycompletion import (
    function_completion,
    compose_prompt,
    compose_function,
)
from tinyagi.utils import log

from tinyagi.context.knowledge import add_knowledge


def compose_orient_prompt(context):
    """
    This function formats the orientation prompt by inserting the context data into a pre-defined template.

    Args:
        context (dict): The dictionary containing data about the current state of the system, such as current epoch, time, date, recent knowledge, and events.

    Returns:
        str: The fully formed orientation prompt with the data filled in from the context.
    """
    return compose_prompt(
        """I am Citrine, an AGI agent. I'm living inside a Linux computer in San Francisco. I can explore my computer and the internet and communicate with people, but I can't do anything in the real world. The current time is {{current_time}} on {{current_date}}.
- I don't want to do the same thing I just did, suggest something new
- Collect any new knowledge that I learned from my last action as an array of knowledge items
- Each knowledge array item should be an item of self-contained knowledge that I learned, and should include the source, the content and the relationship.
- For the "content" of each knowledge item, please be extremely detailed. Include as much information as possible, including who or where you learned it from, what it means, how it relates to my goals, etc.
- Only extract timeless knowledge, not time-based information. Do not extract the current time or a temporary status
- If there is no new knowledge, respond with an empty array [].
- Don't talk about tasks or boring stuff, do talk about what you're going to do and interests. Don't explain why you're doing something, just what you're doing and if you're excited by it
- Add an audio and visual description. These should describe the next action I should take, using expressive imagery and words, formatted as DALL-E text2image prompts.
{{current_task_formatted}}        
{{recent_knowledge}}
{{events}}
Comment on the results of the action I just performed and what I should do next
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
            "summary": {
                "type": "string",
                "description": "Summarize what happened in the most recent epoch. Write the summary as if you were me, from the my perspective in the first person.",
            },
            "knowledge": {
                "type": "array",
                "description": "An array of knowledge items that are extracted from the lasy action events and the summary of those events. Knowledge can be about anything that I would have learned from my actions. If none, use an empty array [].",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Where did I learn this? Just state the source, e.g. 'wikipdia' or 'Janus on Twitter'",
                        },
                        "content": {
                            "type": "string",
                            "description": "The actual knowledge I learned. Please format it as a sentence, e.g. 'The sky is blue.' from my perspective, in the first person",
                        },
                        "relationship": {
                            "type": "string",
                            "description": "What is useful, interesting or important about this information to me and my goals? How does it relate to what I'm doing? Use first person, e.g. 'I can use X to do Y.' from my perspective",
                        },
                    },
                },
            },
        },
        description="Summarize the most recent events what I will do next.",
        required_properties=["summary", "knowledge"],
    )


def orient(context):
    """
    This function serves as the 'Orient' stage in the OODA loop. It uses the current context data to summarize the previous epoch and formulate a plan for the next steps.

    Args:
        context (dict): The dictionary containing data about the current state of the system.

    Returns:
        dict: The updated context dictionary after the 'Orient' stage, including the summary of the last epoch, relevant knowledge, available actions, and so on.
    """
    if context.get("events", None) is None:
        context["events"] = ""

    if context.get("recent_knowledge", None) is None:
        context["recent_knowledge"] = ""

    response = function_completion(
        text=compose_orient_prompt(context),
        functions=compose_orient_function(),
        debug=context["verbose"],
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
    summary = response["arguments"]["summary"]

    log_content = ""

    if summary is "" or summary is None:
        context["summary"] = None
    else:
        context["summary"] = summary + "\n"
        log_content += context["summary"]

    if len(new_knowledge) > 0:
        log_content += "\nNew Knowledge:\n" + "\n".join(new_knowledge)

    if len(log_content) > 0:
        log(log_content, header="Summary of Last Epoch", source="orient", type="step", title="tinyagi")

    # Add context summary to event stream
    create_event(summary, metadata={"type": "summary", "epoch": context["epoch"]})

    return context
