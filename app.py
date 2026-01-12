from flask import Flask, render_template, request, redirect, session, send_file
import os
import psycopg2
from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ======================
# CONFIGURACIÓN
# ======================

app = Flask(__name__)
app.secret_key = "algo-secreto"

MESES = [
    "2026-01", "2026-02", "2026-03", "2026-04",
    "2





















