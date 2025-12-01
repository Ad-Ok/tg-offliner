from flask import Blueprint, request, jsonify
from models import db, Edit
from datetime import datetime
import json

edits_bp = Blueprint('edits', __name__)

@edits_bp.route('/api/edits', methods=['POST'])
def create_or_update_edit():
    """Создание новой записи о правке поста или обновление существующей"""
    try:
        data = request.get_json()
        
        # Валидация данных
        required_fields = ['telegram_id', 'channel_id', 'changes']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Ищем существующую запись для данного поста
        existing_edit = Edit.query.filter_by(
            telegram_id=data['telegram_id'],
            channel_id=data['channel_id']
        ).first()
        
        if existing_edit:
            # Обновляем существующую запись
            existing_edit.date = datetime.now().isoformat()
            existing_edit.changes = data['changes']
            edit = existing_edit
            action = 'updated'
        else:
            # Создаем новую запись
            edit = Edit(
                telegram_id=data['telegram_id'],
                channel_id=data['channel_id'],
                date=datetime.now().isoformat(),
                changes=data['changes']
            )
            db.session.add(edit)
            action = 'created'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'edit_id': edit.id,
            'action': action,
            'message': f'Edit {action} successfully'
        }), 201 if action == 'created' else 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@edits_bp.route('/api/edits/<int:telegram_id>/<channel_id>', methods=['GET'])
def get_edit_for_post(telegram_id, channel_id):
    """Получение правки для конкретного поста (только одна актуальная запись)"""
    try:
        edit = Edit.query.filter_by(
            telegram_id=telegram_id,
            channel_id=channel_id
        ).first()
        
        if edit:
            edit_data = {
                'id': edit.id,
                'telegram_id': edit.telegram_id,
                'channel_id': edit.channel_id,
                'date': edit.date,
                'changes': edit.changes
            }
            return jsonify({
                'success': True,
                'edit': edit_data
            }), 200
        else:
            return jsonify({
                'success': True,
                'edit': None,
                'message': 'No edits found for this post'
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@edits_bp.route('/api/edits', methods=['GET'])
def get_all_edits():
    """Получение всех правок"""
    try:
        edits = Edit.query.all()
        
        edits_data = []
        for edit in edits:
            edits_data.append({
                'id': edit.id,
                'telegram_id': edit.telegram_id,
                'channel_id': edit.channel_id,
                'date': edit.date,
                'changes': edit.changes
            })
        
        return jsonify({
            'success': True,
            'edits': edits_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@edits_bp.route('/api/edits/<channel_id>', methods=['GET'])
def get_edits_for_channel(channel_id):
    """Получение всех правок для канала"""
    try:
        edits = Edit.query.filter_by(channel_id=channel_id).all()
        
        edits_data = []
        for edit in edits:
            edits_data.append({
                'id': edit.id,
                'telegram_id': edit.telegram_id,
                'channel_id': edit.channel_id,
                'date': edit.date,
                'changes': edit.changes
            })
        
        return jsonify({
            'success': True,
            'edits': edits_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@edits_bp.route('/api/edits/<channel_id>', methods=['DELETE'])
def delete_edits_for_channel(channel_id):
    """Удаление всех правок для канала"""
    try:
        # Находим все правки для канала
        edits = Edit.query.filter_by(channel_id=channel_id).all()
        count = len(edits)
        
        if count == 0:
            return jsonify({
                'success': True,
                'message': f'No edits found for channel {channel_id}',
                'deleted_count': 0
            }), 200
        
        # Удаляем все правки
        for edit in edits:
            db.session.delete(edit)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {count} edits for channel {channel_id}',
            'deleted_count': count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
