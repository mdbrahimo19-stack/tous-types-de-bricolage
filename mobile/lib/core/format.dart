import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

/// Les DecimalField DRF arrivent en chaîne ("1500.00").
double? toDouble(dynamic v) {
  if (v == null) return null;
  if (v is num) return v.toDouble();
  return double.tryParse(v.toString());
}

String money(dynamic v) {
  final d = toDouble(v);
  if (d == null) return '—';
  return '${NumberFormat.decimalPattern('fr').format(d.round())} DA';
}

String dateTime(dynamic iso) {
  if (iso == null) return '—';
  final d = DateTime.tryParse(iso.toString());
  if (d == null) return '—';
  return DateFormat('dd/MM/yyyy HH:mm').format(d.toLocal());
}

String dateOnly(dynamic iso) {
  if (iso == null) return '—';
  final d = DateTime.tryParse(iso.toString());
  if (d == null) return '—';
  return DateFormat('dd/MM/yyyy').format(d.toLocal());
}

const urgencies = ['immediate', 'today', 'this_week', 'flexible'];

/// Couleur d'un statut de demande.
Color statusColor(String status) {
  switch (status) {
    case 'published':
      return Colors.blue;
    case 'quotes_received':
      return Colors.orange;
    case 'assigned':
    case 'in_progress':
      return Colors.indigo;
    case 'completed':
    case 'evaluated':
    case 'closed':
      return Colors.green;
    case 'cancelled':
    case 'expired':
      return Colors.grey;
    default:
      return Colors.blueGrey;
  }
}

/// Icône Material la plus proche du nom d'icône du catalogue.
IconData categoryIcon(String? name) {
  switch (name) {
    case 'pipe':
      return Icons.plumbing;
    case 'bolt':
      return Icons.electrical_services;
    case 'air-conditioning':
      return Icons.ac_unit;
    case 'paint-roller':
      return Icons.format_paint;
    case 'wall':
      return Icons.foundation;
    case 'hammer':
      return Icons.carpenter;
    case 'washing-machine':
      return Icons.local_laundry_service;
    case 'spray':
      return Icons.cleaning_services;
    case 'plant':
      return Icons.yard;
    case 'truck':
      return Icons.local_shipping;
    case 'car-wrench':
      return Icons.car_repair;
    case 'car-battery':
      return Icons.battery_charging_full;
    case 'computer':
      return Icons.computer;
    case 'tv':
      return Icons.tv;
    default:
      return Icons.handyman;
  }
}
