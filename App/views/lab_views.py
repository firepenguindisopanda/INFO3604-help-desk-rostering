from flask import Blueprint, jsonify, request, render_template
from App.controllers.lab import L1Question1, L1Question2
from ortools.linear_solver import pywraplp

# Give the blueprint a unique name and URL prefix
lab_bp = Blueprint('lab_blueprint', __name__)

@lab_bp.route('/solve_q1', methods=['POST'])
def solve_q1():
    try:
        data = request.get_json()
        perimeter = float(data['perimeter'])
        
        if perimeter <= 0:
            return jsonify({'error': 'Perimeter must be positive'}), 400
            
        length, width, area = L1Question1(perimeter)
        
        return jsonify({
            'length': length,
            'width': width,
            'area': area
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@lab_bp.route('/solve_q2', methods=['POST'])
def solve_q2():
    try:
        data = request.get_json()
        max_a = float(data['max_a'])
        max_b = float(data['max_b'])
        resource_constraint = float(data['resource_constraint'])
        
        if any(x <= 0 for x in [max_a, max_b, resource_constraint]):
            return jsonify({'error': 'All constraints must be positive'}), 400
            
        a, b, profit = L1Question2(max_a, max_b, resource_constraint)
        
        return jsonify({
            'a': a,
            'b': b,
            'profit': profit
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400
