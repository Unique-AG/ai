# MCP Fundamentals

## 📌 Overview

This document covers the fundamental components and concepts used when building HTTP-streamable MCP (Model Context Protocol) servers. These principles apply across different MCP applications, regardless of the specific tools or functionality they provide.

**Key Concept**: HTTP-streamable MCP servers differ from local MCP servers in that they:
- Are accessible over HTTP/HTTPS
- Require authentication and authorization
- Can be used by web-based clients (like Unique AI)
- Enable secure, user-identified access without requiring local installations
- Support browser-based development tools (like MCP Inspector)

## 🔐 Authentication & Identity

### Purpose
Authentication ensures that only authorized users can access your MCP server. It enables:
- **User identification**: Knowing who is making requests
- **Authorization**: Controlling what users can do
- **Auditing**: Tracking user actions
- **Security**: Protecting your server and resources

### Core Components

#### OAuth2 Flow
OAuth2 is the standard protocol for authentication. It involves:
- **Authorization endpoint**: Where users are redirected to log in
- **Token endpoint**: Where access tokens are exchanged
- **Revocation endpoint**: Where tokens can be invalidated
- **Client credentials**: Your application's ID and secret

#### JWT Verification
JSON Web Tokens (JWTs) are used to verify the identity of users:
- **JWKS (JSON Web Key Set)**: Public keys used to verify token signatures
- **Issuer validation**: Ensures tokens come from your trusted identity provider
- **Token extraction**: Access tokens are extracted from request headers

#### Identity Provider (IdP)
Your identity provider (like Zitadel, Entra ID, Auth0, etc.) handles:
- User authentication
- Token issuance
- User profile management
- Scope management

### Common Scopes
MCP applications typically use these OAuth scopes:
- `openid`, `email`, `profile`: Standard OpenID Connect scopes for user identity
- `mcp:tools`: Permission to access MCP tools
- `mcp:prompts`: Permission to access MCP prompts
- `mcp:resources`: Permission to access MCP resources
- `mcp:resource-templates`: Permission to access resource templates

### User Lookup
After authentication, you typically need to:
1. Extract the access token from the request
2. Call your IdP's "me" endpoint (or equivalent) to get user details
3. Use this information to personalize behavior or enforce permissions

### Environment Configuration
Common environment variables needed:
- **IdP URL**: Base URL of your identity provider
- **Client credentials**: OAuth client ID and secret
- **Base URL**: Public URL where your MCP server is accessible
- **Optional**: Application-specific variables (user IDs, company IDs, etc.)

## ⚙️ FastMCP Server Setup

### Server Initialization
FastMCP is the framework for building HTTP-streamable MCP servers. Key aspects:
- **Name/Title**: Identifies your server
- **Auth configuration**: Attaches authentication to your server
- **Debug mode**: Enables detailed logging during development
- **Transport**: Set to `http` for HTTP-streamable servers

### Server Capabilities
An MCP server can expose:
- **Tools**: Functions that can be called by clients
- **Prompts**: Reusable prompt templates
- **Resources**: Data or content that can be accessed
- **Resource Templates**: Templates for creating resources

## 🛠️ MCP Tools

### Tool Definition
Tools are the core functionality of your MCP server. Each tool has:
- **Name**: Unique identifier
- **Title**: Human-readable name
- **Description**: What the tool does (helps LLMs select the right tool)
- **Parameters**: Inputs with types and descriptions
- **Return type**: What the tool returns

### Tool Metadata
Metadata provides additional context:
- **Unique AI hints**: Custom metadata like icons or system prompts
- **Type annotations**: Using Pydantic and typing for precise schemas
- **Parameter descriptions**: Helps LLMs understand when to use each parameter

### Tool Execution
When a tool is called:
1. Parameters are validated against the schema
2. The tool function executes
3. Results are returned to the client
4. Errors are handled and reported

## 🧩 Standard HTTP Routes

### Combining MCP with HTTP
MCP servers can also expose standard HTTP routes alongside MCP tools:
- **Health checks**: Simple endpoints to verify server status
- **Static assets**: Serve files like favicons, images, etc.
- **Custom endpoints**: Non-MCP functionality (webhooks, status pages, etc.)

### Use Cases
Standard routes are useful for:
- Monitoring and observability
- Serving static content
- Integration with non-MCP clients
- Administrative functions

## 🌐 CORS & Browser Compatibility

### Why CORS Matters
Cross-Origin Resource Sharing (CORS) is essential when:
- Testing with browser-based tools (MCP Inspector)
- Using web-based clients
- Developing locally with different origins

### CORS Configuration
Typical CORS setup includes:
- **Allowed origins**: Which domains can access your server
- **Allowed methods**: Which HTTP methods are permitted
- **Allowed headers**: Which headers can be sent
- **Credentials**: Whether cookies/auth headers are allowed

### Development vs Production
- **Development**: Often allows all origins for simplicity
- **Production**: Should restrict to specific trusted origins

## 🚀 Server Deployment

### Public Accessibility
HTTP MCP servers must be:
- **Publicly reachable**: Accessible via a public URL (not just localhost)
- **HTTPS recommended**: Secure connections for production
- **Base URL configuration**: Correctly configured for OAuth redirects

### Common Deployment Methods
- **Direct hosting**: Deploy to a cloud provider
- **Reverse proxy**: Use nginx, Traefik, etc.
- **Tunneling**: Use ngrok or similar for development/testing
- **Containerization**: Docker for consistent deployment

### Server Configuration
When running the server:
- **Transport**: Must be `http` for HTTP-streamable servers
- **Host/Port**: Where the server listens
- **Middleware**: CORS and other middleware configuration
- **Logging**: Appropriate log levels for development/production

## 🔄 Identity Provider Flexibility

### Swappable IdPs
The authentication system is designed to work with different identity providers:
- **Zitadel**: Open-source identity platform
- **Entra ID (Azure AD)**: Microsoft's identity solution
- **Auth0**: Auth0 platform
- **Okta**: Okta identity provider
- **Any OAuth2/OIDC provider**: Standard protocols ensure compatibility

### Adaptation Requirements
When switching IdPs, you need to:
- Update JWKS URI and issuer URLs
- Adjust OAuth endpoint URLs
- Configure scopes according to provider capabilities
- Ensure client registration matches provider requirements
- Adapt user lookup endpoints if they differ

### Standard Protocols
The use of standard protocols (OAuth2, OIDC, JWT) ensures:
- **Interoperability**: Works with any compliant provider
- **Security**: Industry-standard security practices
- **Flexibility**: Easy to switch providers or support multiple

## 🔗 Component Integration

### How Components Work Together

1. **Client Request** → Client sends request with authentication
2. **Auth Verification** → JWT verifier validates the token
3. **User Identification** → User info retrieved from IdP
4. **Tool Execution** → MCP tool processes the request
5. **Response** → Results returned to client

### Request Flow
```
Client → OAuth Proxy → JWT Verification → User Lookup → Tool Execution → Response
```

### Error Handling
Each component should handle errors gracefully:
- **Auth failures**: Return appropriate 401/403 responses
- **Tool errors**: Provide clear error messages
- **Network issues**: Handle timeouts and connection problems
- **Validation errors**: Return detailed parameter validation errors

## 📋 Best Practices

### Security
- Always use HTTPS in production
- Validate all inputs
- Implement rate limiting
- Log security events
- Keep dependencies updated

### Development
- Use debug mode during development
- Enable detailed logging
- Test with MCP Inspector
- Validate OAuth flows thoroughly

### Documentation
- Document all tools clearly
- Provide examples
- Explain authentication requirements
- Include troubleshooting guides

### Performance
- Optimize tool execution
- Cache where appropriate
- Monitor resource usage
- Handle concurrent requests efficiently

## 🎯 Summary

Building an HTTP-streamable MCP server involves:
1. **Setting up authentication** with OAuth2/JWT and an identity provider
2. **Initializing FastMCP** with proper configuration
3. **Defining tools** with clear schemas and metadata
4. **Configuring CORS** for browser compatibility
5. **Deploying publicly** with proper base URL configuration
6. **Maintaining flexibility** to work with different identity providers

These fundamentals apply regardless of the specific functionality your MCP server provides, whether it's simple calculations, search capabilities, or complex business logic.

