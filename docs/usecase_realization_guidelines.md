# Usecase Implementation Guidelines

You have a usecase in mind that you want to implement on the Unique Platform. You have a few options to do this:


## Option 1: Customize the prompts and configurations of Unique AI

This is the most common and easiest way to get started with your use case. We recommend this as the go to option for most use cases.

### When to go this route?

- You want to customize the response of the agent to have a specific format or structure.
- You want to work with the web or existing documents in the knowledge base.
- You want to work converse with your own files that are not in the knowledge base but can be uploaded on a conversational basis.
- You want to have a translator with a tailored glossary.

It is best to study existing agents provided on the platform to get an idea of how to customize the agent to your needs. You can find them in the [Unique AI Space Documentation](https://unique-ch.atlassian.net/wiki/spaces/PUBDOC/pages/1385235119/Space+Management+for+Admins).

### How to go this route?

UniqueAI is a powerful agent/orchestrator that can be customized to your needs. You can customize the prompts, knowledge base access and tools available to the agent to tailor it to your needs.

You can find more information about it here: [Unique AI Space Documentation](https://unique-ch.atlassian.net/wiki/spaces/PUBDOC/pages/1405878956/Unique+AI+Space)


## Option 2: Develop a MCP Server and integrate it with Unique AI

If you find yourself in a situation where some information is missing from Unique's knowledge base or some tools are missing then you can develop a MCP server to integrate the external knowledge source or tool into Unique AI. This strategy gives you the ability to integrate your own data and logic with Unique AI while still taking full advantage of Unique AI's other tools and capabilities.

### When to go this route?

- You want to integrate an external knowledge source to Unique AI. The external knowledge source can be a knowledge base, a database, a file, a website, a API, etc.
- You want to connect a proprietary tool to Unique AI. 

### How to go this route?

You can find detailed examples of how to develop MCP servers and integrate them with Unique AI in the [Unique Toolkit Documentation](../Tutorials/mcp).

## Option 3: Develop a Custom Module/Agent

You ofcourse have the option to develop an entirely new agent from scratch. This is the most flexible option and give you the most control over the agent. But this flexibility comes at a cost of time and effort, not to mention the lack of integration with Unique AI's other tools and capabilities.

### When to go this route?

- You find yourself in a situation where the above two options are not sufficient to solve your problem.
- You want to have better control over the orchestration agent.
- You have a very clear/rigid workflow that you want to implement.

### How to go this route?

You can find detailed examples of how to develop custom modules using the Unique Toolkit in the [Unique Toolkit Documentation](../unique-toolkit/application_types/event_driven).


## Option 4: Develop standalone Application

### When to go this route?

- You want to develop a GENERATIVE AI application that does not interact with the user directly via Unique's web interface but 
    - still collect useful statistics and analytics via the Unique Platform.
    - use/populate knoledge base content to run some background tasks.
    - run some batch scripts that run periodically.

### How to go this route?

You can find detailed examples of how to develop standalone applications using the Unique Toolkit in the [Unique Toolkit Documentation](../unique-toolkit/application_types/standalone_application.md).

