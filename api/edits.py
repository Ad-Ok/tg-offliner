from flask import Blueprint, request, jsonify
from models import db, Edit
from datetime import datetime
import json

edits_bp = Blueprint('edits', __name__)

@edits_bp.route('/api/edits', methods=['POST'])
def create_edit():
    """Создание новой записи о правке поста"""
    try:
        data = request.get_json()
        
        # Валидация данных
        required_fields = ['telegram_id', 'channel_id', 'changes']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Создание новой записи
        edit = Edit(
            telegram_id=data['telegram_id'],
            channel_id=data['channel_id'],
            date=datetime.now().isoformat(),
            changes=data['changes']
        )
        
        db.session.add(edit)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'edit_id': edit.id,
            'message': 'Edit created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@edits_bp.route('/api/edits/<int:telegram_id>/<channel_id>', methods=['GET'])
def get_edits_for_post(telegram_id, channel_id):
    """Получение всех правок для конкретного поста"""
    try:
        edits = Edit.query.filter_by(
            telegram_id=telegram_id,
            channel_id=channel_id
        ).all()
        
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
