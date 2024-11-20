from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


# --- OpenTelemetry Configuration ---
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)  # Collector's OTLP endpoint
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

# --- Flask Application Setup ---
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

# --- Database Configuration ---
DATABASE_URL = "sqlite:///users.db"
engine = create_engine(DATABASE_URL, echo=True)
SQLAlchemyInstrumentor().instrument(engine=engine)

Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# --- Database Model ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

Base.metadata.create_all(engine)

# --- API Routes ---
@app.route("/user", methods=["POST"])
def add_user():
    data = request.json

    # Validate input
    if not data or not data.get("name") or not data.get("email"):
        return jsonify({"error": "Invalid input"}), 400

    try:
        # Add user to the database
        new_user = User(name=data["name"], email=data["email"])
        session.add(new_user)
        session.commit()

        return jsonify({"message": "User added successfully", "user": {"id": new_user.id, "name": new_user.name, "email": new_user.email}}), 201
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/users", methods=["GET"])
def get_users():
    users = session.query(User).all()
    return jsonify([{"id": user.id, "name": user.name, "email": user.email} for user in users])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
