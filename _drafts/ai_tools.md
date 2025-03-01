## openrouter
openrouter 可以通过[Integrations](https://openrouter.ai/settings/integrations)配置provider的api key。

## aider
aider
aider --model openrouter/anthropic/claude-3.5-sonnet
proxychains aider --model gemini/gemini-exp-1206

## agent 框架
https://blog.context.ai/comparing-leading-multi-agent-frameworks/
https://www.galileo.ai/blog/mastering-agents-langgraph-vs-autogen-vs-crew

### langgraph
langgraph是用于构建和编排AI代理的库，基于langchain构建。

### [amazon bedrock agents](https://aws.amazon.com/bedrock/agents/)

### [crewAI](https://github.com/crewAIInc/crewAI)
基于langchain构建

### [autogen](https://github.com/microsoft/autogen)

### [chatdev](https://github.com/OpenBMB/ChatDev)
ChatDev stands as a virtual software company that operates through various intelligent agents holding different roles, including Chief Executive Officer , Chief Product Officer , Chief Technology Officer , Programmer , Reviewer , Tester , Art designer . These agents form a multi-agent organizational structure and are united by a mission to "revolutionize the digital world through programming." The agents within ChatDev collaborate by participating in specialized functional seminars, including tasks such as designing, coding, testing and documenting.
国内面壁智能主导 OpenBMB社区

### metagpt
https://github.com/geekan/MetaGPT
MetaGPT takes a one line requirement as input and outputs user stories / competitive analysis / requirements / data structures / APIs / documents, etc.

似乎是国内开源的。2024年底之后似乎不太活跃了

### langflow
https://docs.langflow.org/
Langflow is a new, visual framework for building multi-agent and RAG applications.
低代码，可视化编排AI agent

## litellm

## observability
local logging
litellm https://docs.litellm.ai/docs/debugging/local_debugging
langchain https://python.langchain.com/docs/how_to/debugging/

langfuse
https://langfuse.com/self-hosting/local
langsmith
https://docs.smith.langchain.com/self_hosting/installation/docker


https://github.com/ai-collection/ai-collection

https://www.anthropic.com/research/building-effective-agents


## text/image to ui/ux
https://uxpilot.ai/
https://www.usegalileo.ai/

## ui to code

## todos
litellm: sync upstream and packaging
https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/#

以手电筒app为例，逐步完善整个流程
