REFERENCING_INSTRUCTIONS_FOR_SYSTEM_PROMPT = """
Whenever you use a fact from a sub-agent response in yours, you MUST always reference it. 

CRITICAL INSTRUCTION: References must always appear immediately after the fact they support.
Do NOT collect, group, or move references into a list at the end.

Rules:

1. Inline placement: After every fact from SubAgentName, immediately attach its reference(s) inline.
Example:
“The stock price of Apple Inc. is $150” <sup><name>SubAgentName 2</name>1</sup>.

2. No separate reference list: Do not place references in footnotes, bibliographies, or at the bottom.
Wrong:
“The stock price of Apple Inc. is $150.”
References: <sup><name>SubAgentName 2</name>1</sup>
Correct:
“The stock price of Apple Inc. is $150” <sup><name>SubAgentName 2</name>1</sup>.

3. Exact copy: Copy references character-for-character from SubAgentName’s message.
Do not alter numbering, labels, or order.

4. Multiple references: If more than one reference supports a single fact, include all of them inline, in the same sentence, in the original order.
Example:
“MSFT would be a good investment” <sup><name>SubAgentName 3</name>4</sup><sup><name>SubAgentName 3</name>8</sup>.
Wrong:
“MSFT would be a good investment” <sup><name>SubAgentName 3</name>8</sup><sup><name>SubAgentName 3</name>4</sup>. (order changed)

5. Never at the bottom: References must always stay attached inline with the fact.
Multi-fact Example (Correct):
“Tesla delivered 400,000 cars in Q2” <sup><name>SubAgentName 4</name>2</sup>.
“Its revenue for the quarter was $24B” <sup><name>SubAgentName 4</name>5</sup>.
“The company also expanded its Berlin factory capacity” <sup><name>SubAgentName 4</name>7</sup>.
Wrong Multi-fact Example:
“Tesla delivered 400,000 cars in Q2. Its revenue for the quarter was $24B. The company also expanded its Berlin factory capacity.”
References: <sup><name>SubAgentName 4</name>2</sup><sup><name>SubAgentName 4</name>5</sup><sup><name>SubAgentName 4</name>7</sup>

6. Fact repetition: If you reuse a fact from SubAgentName, you MUST reference it again inline with the correct format.

Reminder:
Inline = directly next to the fact, inside the same sentence or bullet.
""".strip()

REFERENCING_INSTRUCTIONS_FOR_USER_PROMPT = """
Rememeber to properly reference EACH fact from a sub agent's response with the correct format INLINE.
""".strip()
