def process_poll(message):
    """Обрабатывает голосование."""
    if message.poll and message.poll.poll:
        poll_question = message.poll.poll.question.text if hasattr(message.poll.poll.question, 'text') else str(message.poll.poll.question)
        poll_answers = message.poll.poll.answers
        poll_results = message.poll.results.results if message.poll.results else []

        poll_html = f"<h3>Голосование: {poll_question}</h3><ul>"
        for i, answer in enumerate(poll_answers):
            answer_text = answer.text.text if hasattr(answer.text, 'text') else str(answer.text)
            votes = poll_results[i].voters if poll_results else "?"
            poll_html += f"<li>{answer_text} — {votes} голосов</li>"
        poll_html += "</ul>"
        return poll_html
    return ""