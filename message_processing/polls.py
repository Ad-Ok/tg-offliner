import logging

def process_poll(message):
    """Обрабатывает голосование."""
    if hasattr(message, 'poll') and message.poll and hasattr(message.poll, 'poll') and message.poll.poll:
        try:
            logging.info(f"Обрабатывается голосование в сообщении {getattr(message, 'id', 'unknown')}")
            
            # Получаем вопрос голосования
            poll_question = message.poll.poll.question.text if hasattr(message.poll.poll.question, 'text') else str(message.poll.poll.question)
            poll_answers = message.poll.poll.answers
            poll_results = message.poll.results.results if (message.poll.results and hasattr(message.poll.results, 'results')) else []

            # Вычисляем общее количество голосов для расчета процентов
            total_votes = 0
            votes_per_answer = []
            
            for i, answer in enumerate(poll_answers):
                votes = 0
                if i < len(poll_results) and hasattr(poll_results[i], 'voters'):
                    votes = poll_results[i].voters
                votes_per_answer.append(votes)
                total_votes += votes

            poll_html = f"<h3 class='text-2xl mb-4'>{poll_question}</h3><div class='poll-results'>"
            
            for i, answer in enumerate(poll_answers):
                answer_text = answer.text.text if hasattr(answer.text, 'text') else str(answer.text)
                votes = votes_per_answer[i]
                
                # Вычисляем процент
                percentage = 0
                if total_votes > 0:
                    percentage = (votes / total_votes) * 100
                
                # Формируем HTML для каждого варианта ответа
                poll_html += f"""
                <div class="poll-option mb-2">
                    <div class="mb-1">
                        <strong>{percentage:.1f}%</strong> - {answer_text} ({votes})
                    </div>
                    <progress max="100" value="{percentage:.1f}" class="progress w-full"></progress>
                </div>
                """
            
            poll_html += "</div>"
            logging.info(f"Голосование успешно обработано: {poll_question}")
            return poll_html
        except Exception as e:
            logging.warning(f"Ошибка при обработке голосования: {e}")
            # В случае ошибки возвращаем базовую информацию о голосовании
            return "<h3>📊 Голосование (детали недоступны)</h3>"
    return ""