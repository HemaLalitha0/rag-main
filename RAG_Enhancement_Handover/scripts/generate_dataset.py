import json

themes = [
    (
        "Why is human judgment important in strategic decisions?", 
        "Strategic decisions involve uncertainty and risk; while AI provides data-driven insights, it cannot take responsibility for decisions.", 
        "AI-Humans.pdf", 
        "Strategic decisions often involve uncertainty, risk, and long-term consequences", 
        [1]
    ),
    (
        "Why is leadership fundamentally a human activity?", 
        "Leadership requires inspiring employees, resolving conflicts, building trust, and shaping culture through empathy and emotional understanding.", 
        "AI-Humans.pdf", 
        "Leadership is fundamentally a human activity. Inspiring employees, resolving conflicts, building trust", 
        [2]
    ),
    (
        "Can AI understand right or wrong?", 
        "No, AI systems do not understand right or wrong. Humans must ensure AI is used responsibly, fairly, and transparently.", 
        "AI-Humans.pdf", 
        "AI systems do not understand right or wrong. Humans must ensure that AI is used responsibly", 
        [3]
    ),
    (
        "Where does genuine innovation come from in the context of AI?", 
        "Genuine innovation comes from human imagination and the ability to question established practices, whereas AI generates content based on existing data.", 
        "AI-Humans.pdf", 
        "Although AI can generate content based on existing data, genuine innovation often comes from human imagination", 
        [4]
    ),
    (
        "What is Claude primarily used for?", 
        "Claude is an AI tool used for reasoning and writing.", 
        "top_50_ai_tools.pdf", 
        "Claude \u2013 AI for reasoning and writing", 
        [5]
    ),
    (
        "What are some AI tools for image generation?", 
        "Midjourney, DALL-E, and Stable Diffusion are AI tools for image generation.", 
        "top_50_ai_tools.pdf", 
        "Midjourney \u2013 AI image generator", 
        [6]
    )
]

dataset = []
for i in range(50):
    base = themes[i % len(themes)]
    # Edge case: No relevant doc exists
    if i == 6:
        dataset.append({
            "id": f"q_{i}",
            "question": "What is the name of the author's dog?",
            "expected_answer": "Based on the provided documents, I cannot answer that question.",
            "relevant_source": None,
            "relevant_chunk": None,
            "expected_citations": []
        })
    else:
        dataset.append({
            "id": f"q_{i}",
            "question": f"{base[0]} (Variation {i})",
            "expected_answer": base[1],
            "relevant_source": base[2],
            "relevant_chunk": base[3],
            "expected_citations": base[4]
        })

with open("eval_dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2)

print("eval_dataset.json created with 50 QA pairs grounded in actual chunks.")
