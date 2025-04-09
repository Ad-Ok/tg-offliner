def process_reactions(message):
    """Обрабатывает реакции."""
    if message.reactions:
        reactions_html = "<div class='reactions'>"
        for reaction in message.reactions.results:
            emoji = reaction.reaction.emoticon if hasattr(reaction.reaction, 'emoticon') else str(reaction.reaction)
            count = reaction.count
            reactions_html += f"<span>{emoji} {count}</span> "
        reactions_html += "</div>"
        return reactions_html
    return ""