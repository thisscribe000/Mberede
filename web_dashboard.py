import io
import csv
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, send_file, redirect, url_for
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from core.models import User, EmergencyContact, AccessLog, SOSLog, get_db
from core.config import config

app = Flask(__name__)
app.config["SECRET_KEY"] = config.secret_key

STATS_TEMPLATE = """
<!doctype html>
<html>
<head>
<title>Mberede Admin</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f4f4f9; color: #333; }
  .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
  h1 { color: #2c3e50; margin-bottom: 5px; }
  .subtitle { color: #666; margin-bottom: 30px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
  .card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  .card h3 { font-size: 14px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  .card .value { font-size: 32px; font-weight: 700; color: #2c3e50; }
  .card .sub { font-size: 12px; color: #aaa; margin-top: 4px; }
  .card.blue .value { color: #3498db; }
  .card.green .value { color: #27ae60; }
  .card.orange .value { color: #e67e22; }
  .card.red .value { color: #e74c3c; }
  table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  th { background: #2c3e50; color: white; padding: 12px 16px; text-align: left; font-size: 13px; }
  td { padding: 10px 16px; border-bottom: 1px solid #eee; font-size: 13px; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #f8f9fa; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
  .badge.green { background: #d4edda; color: #155724; }
  .badge.red { background: #f8d7da; color: #721c24; }
  .badge.orange { background: #fff3cd; color: #856404; }
  .export { margin: 20px 0; }
  .export a { display: inline-block; padding: 8px 16px; background: #2c3e50; color: white; text-decoration: none; border-radius: 8px; font-size: 13px; margin-right: 10px; }
  .export a:hover { background: #34495e; }
  .timestamp { color: #888; font-size: 12px; }
</style>
</head>
<body>
<div class="container">
  <h1>Mberede Admin</h1>
  <p class="subtitle">System Analytics Dashboard — Updated just now</p>

  <div class="grid">
    <div class="card">
      <h3>Total Users</h3>
      <div class="value">{{ stats.total_users }}</div>
      <div class="sub">{{ stats.new_today }} new today</div>
    </div>
    <div class="card blue">
      <h3>Emergency Contacts</h3>
      <div class="value">{{ stats.total_contacts }}</div>
      <div class="sub">{{ stats.verified_contacts }} verified</div>
    </div>
    <div class="card red">
      <h3>SOS Sent (All Time)</h3>
      <div class="value">{{ stats.total_sos }}</div>
      <div class="sub">{{ stats.sos_delivered }} delivered ({{ stats.delivery_rate }}%)</div>
    </div>
    <div class="card orange">
      <h3>SOS Today</h3>
      <div class="value">{{ stats.sos_today }}</div>
      <div class="sub">{{ stats.sos_week }} this week</div>
    </div>
  </div>

  <div class="export">
    <a href="/admin/export/csv">📥 Export CSV</a>
    <a href="/admin/export/json">📥 Export JSON</a>
  </div>

  <h2 style="margin: 30px 0 15px; font-size: 18px;">Recent SOS Events</h2>
  <table>
    <tr><th>Time</th><th>Contact</th><th>Message</th><th>Status</th></tr>
    {% for log in recent_sos %}
    <tr>
      <td><span class="timestamp">{{ log.sent_at }}</span></td>
      <td>{{ log.contact_name }}</td>
      <td>{{ log.message or 'Default message' }}</td>
      <td>
        {% if log.delivered %}
        <span class="badge green">✅ Delivered</span>
        {% else %}
        <span class="badge red">❌ Failed</span>
        {% endif %}
      </td>
    </tr>
    {% else %}
    <tr><td colspan="4" style="text-align:center;color:#888;">No SOS events yet</td></tr>
    {% endfor %}
  </table>

  <h2 style="margin: 30px 0 15px; font-size: 18px;">Recent Users</h2>
  <table>
    <tr><th>Username</th><th>Contacts</th><th>Created</th><th>Last Active</th><th>Status</th></tr>
    {% for u in recent_users %}
    <tr>
      <td>@{{ u.username or u.telegram_id }}</td>
      <td>{{ u.contact_count }}</td>
      <td><span class="timestamp">{{ u.created }}</span></td>
      <td><span class="timestamp">{{ u.last_active }}</span></td>
      <td>
        {% if u.locked %}
        <span class="badge orange">🔒 Locked</span>
        {% else %}
        <span class="badge green">✅ Active</span>
        {% endif %}
      </td>
    </tr>
    {% else %}
    <tr><td colspan="5" style="text-align:center;color:#888;">No users yet</td></tr>
    {% endfor %}
  </table>

  <h2 style="margin: 30px 0 15px; font-size: 18px;">Recent Access Logs</h2>
  <table>
    <tr><th>Time</th><th>Action</th><th>Result</th></tr>
    {% for log in access_logs %}
    <tr>
      <td><span class="timestamp">{{ log.timestamp }}</span></td>
      <td>{{ log.action }}</td>
      <td>
        {% if log.success %}
        <span class="badge green">✅</span>
        {% else %}
        <span class="badge red">❌</span>
        {% endif %}
      </td>
    </tr>
    {% else %}
    <tr><td colspan="3" style="text-align:center;color:#888;">No logs yet</td></tr>
    {% endfor %}
  </table>
</div>
</body>
</html>
"""


def _get_stats(db):
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.pin_hash != None).count()
    total_contacts = db.query(EmergencyContact).count()
    verified_contacts = db.query(EmergencyContact).filter(EmergencyContact.is_verified == True).count()
    total_sos = db.query(SOSLog).count()
    sos_delivered = db.query(SOSLog).filter(SOSLog.delivered == True).count()
    sos_today = db.query(SOSLog).filter(SOSLog.sent_at > datetime.utcnow().replace(hour=0, minute=0, second=0)).count()
    sos_week = db.query(SOSLog).filter(SOSLog.sent_at > datetime.utcnow() - timedelta(days=7)).count()
    new_today = db.query(User).filter(User.created_at > datetime.utcnow().replace(hour=0, minute=0, second=0)).count()
    delivery_rate = round(sos_delivered / total_sos * 100, 1) if total_sos > 0 else 0
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_contacts": total_contacts,
        "verified_contacts": verified_contacts,
        "total_sos": total_sos,
        "sos_delivered": sos_delivered,
        "sos_today": sos_today,
        "sos_week": sos_week,
        "new_today": new_today,
        "delivery_rate": delivery_rate,
    }


@app.route("/admin")
def admin_dashboard():
    db = get_db()
    stats = _get_stats(db)

    recent_sos = []
    for log in db.query(SOSLog).order_by(SOSLog.sent_at.desc()).limit(20).all():
        contact = db.query(EmergencyContact).filter(EmergencyContact.id == log.contact_id).first()
        recent_sos.append({
            "sent_at": _ago(log.sent_at),
            "contact_name": contact.name if contact else "Unknown",
            "message": log.message,
            "delivered": log.delivered,
        })

    recent_users = []
    for u in db.query(User).filter(User.pin_hash != None).order_by(User.created_at.desc()).limit(20).all():
        contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == u.id).count()
        locked = u.locked_until and u.locked_until > datetime.utcnow()
        recent_users.append({
            "username": u.telegram_username,
            "telegram_id": u.telegram_user_id,
            "contact_count": contacts,
            "created": _ago(u.created_at),
            "last_active": _ago(u.last_accessed_at) if u.last_accessed_at else "Never",
            "locked": locked,
        })

    access_logs = []
    for log in db.query(AccessLog).order_by(AccessLog.timestamp.desc()).limit(20).all():
        access_logs.append({
            "timestamp": _ago(log.timestamp),
            "action": log.action,
            "success": log.success,
        })

    return render_template_string(STATS_TEMPLATE,
        stats=stats,
        recent_sos=recent_sos,
        recent_users=recent_users,
        access_logs=access_logs,
    )


@app.route("/admin/export/csv")
def export_csv():
    db = get_db()
    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow(["Users"])
    writer.writerow(["Telegram Username", "User ID", "Contacts", "Created", "Last Active"])
    for u in db.query(User).filter(User.pin_hash != None).all():
        contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == u.id).count()
        writer.writerow([u.telegram_username, u.telegram_user_id, contacts, u.created_at, u.last_accessed_at])

    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"mberede_export_{datetime.utcnow().strftime('%Y%m%d')}.csv",
    )


@app.route("/admin/export/json")
def export_json():
    import json
    db = get_db()
    data = _get_stats(db)
    data["recent_users"] = [
        {"username": u.telegram_username, "user_id": u.telegram_user_id}
        for u in db.query(User).filter(User.pin_hash != None).limit(100).all()
    ]
    return send_file(
        io.BytesIO(json.dumps(data, indent=2, default=str).encode()),
        mimetype="application/json",
        as_attachment=True,
        download_name=f"mberede_export_{datetime.utcnow().strftime('%Y%m%d')}.json",
    )


def _ago(dt):
    if not dt:
        return "Never"
    diff = datetime.utcnow() - dt
    if diff.total_seconds() < 60:
        return "Just now"
    elif diff.total_seconds() < 3600:
        return f"{int(diff.total_seconds() / 60)}m ago"
    elif diff.total_seconds() < 86400:
        return f"{int(diff.total_seconds() / 3600)}h ago"
    else:
        return f"{int(diff.total_seconds() / 86400)}d ago"


def create_flask_app(bot_app=None):
    if bot_app:
        return DispatcherMiddleware(bot_app, {"/web": app})
    return app
