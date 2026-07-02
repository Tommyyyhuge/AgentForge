# Use Embedded Chroma for Memory

AgentForge stores long-term **Memory** through the backend process using an embedded Chroma persistent client, with the Chroma data directory mounted as backend storage. We chose this instead of running a separate Chroma service in Docker Compose because the standalone Chroma image introduced a startup failure in the current environment, while embedded persistence keeps local deployment simple and preserves the memory retrieval capability.

This decision means Docker Compose runs fewer services and avoids the Chroma container compatibility issue, but memory storage is coupled to the backend deployment. A separate Chroma service can be reconsidered later if AgentForge needs independent scaling, remote vector storage, or a full **Knowledge Base** capability.
