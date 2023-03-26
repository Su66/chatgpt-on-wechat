from bot.session_manager import Session
from common.log import logger
class ChatGPTSession(Session):
    def __init__(self, session_id, system_prompt=None, model= "gpt-3.5-turbo"):
        super().__init__(session_id, system_prompt)
        self.messages = []
        self.model = model
        self.reset()
    
    def reset(self):
        system_item = {'role': 'system', 'content': self.system_prompt}
        self.messages = [system_item]

    def add_query(self, query):
        user_item = {'role': 'user', 'content': query}
        self.messages.append(user_item)

    def add_reply(self, reply):
        assistant_item = {'role': 'assistant', 'content': reply}
        self.messages.append(assistant_item)
    
    def discard_exceeding(self, max_tokens, cur_tokens= None):
        if cur_tokens is None:
            cur_tokens = num_tokens_from_messages(self.messages, self.model)
        while cur_tokens > max_tokens:
            if len(self.messages) > 2:
                self.messages.pop(1)
            elif len(self.messages) == 2 and self.messages[1]["role"] == "assistant":
                self.messages.pop(1)
                cur_tokens = num_tokens_from_messages(self.messages, self.model)
                break
            elif len(self.messages) == 2 and self.messages[1]["role"] == "user":
                logger.warn("user message exceed max_tokens. total_tokens={}".format(cur_tokens))
                break
            else:
                logger.debug("max_tokens={}, total_tokens={}, len(messages)={}".format(max_tokens, cur_tokens, len(self.messages)))
                break
            try:
                cur_tokens = num_tokens_from_messages(self.messages, self.model)
            except Exception as e:
                logger.debug("Exception when counting tokens precisely for query: {}".format(e))
                cur_tokens = cur_tokens - max_tokens
        return cur_tokens
    

# refer to https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
def num_tokens_from_messages(messages, model):
    """Returns the number of tokens used by a list of messages."""
    import tiktoken
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.debug("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    elif model == "gpt-4":
        return num_tokens_from_messages(messages, model="gpt-4-0314")
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model == "gpt-4-0314":
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        logger.warn(f"num_tokens_from_messages() is not implemented for model {model}. Returning num tokens assuming gpt-3.5-turbo-0301.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens