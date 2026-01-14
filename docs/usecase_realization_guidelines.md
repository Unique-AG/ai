# 🎯 Use Case Implementation Guidelines

When implementing a use case on the **Unique Platform**, there are multiple approaches.  
Below is the **recommended starting point for most use cases**.

---

## ⚙️ Option 1: Customize Unique AI (Prompts & Configuration)

This is the **fastest and most common** way to implement a use case — **no custom development required**.

It is best to study **existing agents provided on the platform** to get an idea of how to customize agents for your needs.  
You can find them in the [Unique AI Space Documentation](https://unique-ch.atlassian.net/wiki/spaces/PUBDOC/pages/1385235119/Space+Management+for+Admins).

---

### When to use this option
Choose this if you want to:
- ✨ Control response **format, tone, or structure**
- 📚 Work with **knowledge base documents** or web sources, including **deep research, code interpreter, and other commodity tools**
- 🔌 Integrate **MCP tools** into your use case (see Option 2)
- 📄 Let users **upload and chat with their own files**
- 🌐 Build a **translator with a custom glossary**
- 🧠 Define agent behavior via prompts instead of code

---

### 🧠 Multi-Agent & Sub-Agent Concept

Unique supports **multi-agent systems** using **sub-agents**:

- A **main agent** orchestrates the conversation
- **Sub-agents** handle specialized tasks
- Each sub-agent has its own **prompts, tools, and constraints**
- The main agent delegates tasks and merges results into a single response

You can learn more about designing and configuring sub-agents in the  
[Sub-Agent Documentation](https://unique-ch.atlassian.net/wiki/spaces/PUBDOC/pages/1450246161/Sub+Agent).

---

### 🛠️ How it works

**UniqueAI Chat** acts as an agent orchestrator that can be configured without code.  
You can customize prompts, tools, and knowledge access directly in the AI Space, as described in the  
[Unique AI Space Documentation](https://unique-ch.atlassian.net/wiki/spaces/PUBDOC/pages/1405878956/Unique+AI+Space).

You can configure:
- System and task prompts
- Knowledge base access
- Tools per agent or sub-agent
- Delegation logic between agents

---

### ✅ Why this is recommended
- Fast to implement
- Easy to iterate
- No engineering dependency
- Production-ready
- Supports single- and multi-agent use cases


## 🔌 Option 2: Develop a MCP Server and integrate it with Unique AI

If you find yourself in a situation where some information is missing from Unique's knowledge base or some tools are missing then you can develop a MCP server to integrate the external knowledge source or tool into Unique AI. This strategy gives you the ability to integrate your own data and logic with Unique AI while still taking full advantage of Unique AI's other tools and capabilities.

### 🤔 When to go this route?

- 🔗 You want to integrate an external knowledge source to Unique AI. The external knowledge source can be a knowledge base, a database, a file, a website, a API, etc.
- 🛠️ You want to connect a proprietary tool to Unique AI. 

### 🛠️ How to go this route?

You can find detailed examples of how to develop MCP servers and integrate them with Unique AI in the [tutorials on MCP](../Tutorials/mcp).

## 🏗️ Option 3: Develop a Custom Module/Agent

You ofcourse have the option to develop an entirely new agent from scratch. This is the most flexible option and gives you the most control over the agent. But this flexibility comes at a cost of time and effort, not to mention the lack of integration with Unique AI's other tools and capabilities.

### 🤔 When to go this route?

- 🎯 You find yourself in a situation where the above two options are not sufficient to solve your problem.
- 🎛️ You want to have better control over the orchestration agent.
- 📋 You have a very clear/rigid workflow that you want to implement.

### 🛠️ How to go this route?

You can find instructions and examples of how to develop custom modules using the Unique Toolkit in the [event driven applications](../unique-toolkit/application_types/event_driven) section of this documentation.


## 🚀 Option 4: Develop standalone Application

### 🤔 When to go this route?

- 💡 You want to develop a GENERATIVE AI application that does not interact with the user directly via Unique's web interface but 
    - 📊 still collect useful statistics and analytics via the Unique Platform.
    - 📚 use/populate knoledge base content to run some background tasks.
    - ⏰ run some batch scripts that run periodically.

### 🛠️ How to go this route?

You can find detailed examples of how to develop standalone applications using the Unique Toolkit in the [Unique Toolkit Documentation](../unique-toolkit/application_types/standalone_application.md).

