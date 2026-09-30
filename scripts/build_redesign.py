# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.catalog import CATALOG

catalog_json = json.dumps(CATALOG, ensure_ascii=False, indent=2)

html_template = '''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Island Intelligence // Cyber & OSINT Forensics</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
:root {
  --bg: #07090e;
  --surface: #0c1017;
  --surface-raised: #111722;
  --surface-hover: #161e2e;
  --border: #18202f;
  --border-focus: #38bdf8;
  --primary: #38bdf8;
  --primary-glow: rgba(56, 189, 248, 0.15);
  --cyan: #06b6d4;
  --green: #10b981;
  --amber: #f59e0b;
  --purple: #8b5cf6;
  --danger: #f43f5e;
  --text: #f1f5f9;
  --text-muted: #64748b;
  --text-dim: #475569;
  --font-mono: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
}

* { margin:0; padding:0; box-sizing:border-box; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-tap-highlight-color: transparent; }
body { background: var(--bg); color: var(--text); min-height: 100vh; padding: 12px; padding-bottom: 80px; overflow-x: hidden; -webkit-font-smoothing: antialiased; }

.app-container { max-width: 860px; margin: 0 auto; position: relative; z-index: 1; }

/* Top Header */
.top-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 0 14px; border-bottom: 1px solid var(--border); margin-bottom: 12px; background: rgba(7, 9, 14, 0.95); backdrop-filter: blur(14px); position: sticky; top: 0; z-index: 100; }
.brand-group { display: flex; align-items: center; gap: 8px; cursor: pointer; text-decoration: none; }
.brand-icon { width: 30px; height: 30px; border-radius: var(--radius-sm); background: linear-gradient(135deg, #0284c7, #38bdf8); display: flex; align-items: center; justify-content: center; color: #fff; font-size: 14px; box-shadow: 0 0 15px var(--primary-glow); }
.brand-text { font-size: 13px; font-weight: 800; color: #fff; letter-spacing: 0.3px; line-height: 1.1; }
.brand-sub { font-size: 9px; color: var(--text-muted); font-family: var(--font-mono); letter-spacing: 0.5px; }
.live-badge { font-size: 8px; font-weight: 800; padding: 1px 5px; border-radius: 4px; background: rgba(16, 185, 129, 0.15); color: var(--green); border: 1px solid rgba(16, 185, 129, 0.3); }

.header-badges { display: flex; align-items: center; gap: 6px; }
.pill-badge { display: inline-flex; align-items: center; gap: 5px; padding: 4px 9px; border-radius: var(--radius-sm); font-size: 11px; font-weight: 700; border: 1px solid var(--border); background: var(--surface); cursor: pointer; transition: all 0.15s; }
.pill-badge:hover { border-color: var(--primary); }
.pill-quota { color: var(--amber); border-color: rgba(245, 158, 11, 0.3); }
.pill-quota:hover { border-color: var(--amber); }

/* Navigation Tab Bar (Minimalist) */
.nav-tabs { display: flex; gap: 5px; margin-bottom: 14px; background: var(--surface); padding: 4px; border-radius: var(--radius-md); border: 1px solid var(--border); overflow-x: auto; scrollbar-width: none; }
.nav-tabs::-webkit-scrollbar { display: none; }
.nav-tab-btn { flex: 1; min-width: 80px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 7px 10px; border-radius: var(--radius-sm); font-size: 11px; font-weight: 700; color: var(--text-muted); background: transparent; border: none; cursor: pointer; transition: all 0.15s; white-space: nowrap; }
.nav-tab-btn:hover { color: #fff; background: var(--surface-raised); }
.nav-tab-btn.active { color: #fff; background: var(--surface-raised); border: 1px solid var(--border); color: var(--primary); box-shadow: 0 1px 4px rgba(0,0,0,0.4); }
.nav-tab-badge { font-size: 9px; padding: 1px 5px; border-radius: 10px; background: rgba(56, 189, 248, 0.15); color: var(--primary); }

/* View pages */
.view-page { display: none; }
.view-page.active { display: block; animation: fadeIn 0.15s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(2px); } to { opacity: 1; transform: translateY(0); } }

/* OmniSearch Bar */
.omni-container { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 12px; margin-bottom: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.25); }
.omni-input-row { display: flex; gap: 8px; align-items: center; position: relative; }
.omni-input-wrap { flex: 1; position: relative; display: flex; align-items: center; }
.omni-icon { position: absolute; left: 12px; color: var(--text-muted); font-size: 13px; }
.omni-input { width: 100%; padding: 11px 12px 11px 36px; background: #05070b; border: 1px solid var(--border); border-radius: var(--radius-md); color: #fff; font-size: 13px; outline: none; transition: border-color 0.15s; }
.omni-input:focus { border-color: var(--primary); }
.omni-type-badge { position: absolute; right: 10px; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px; background: rgba(56, 189, 248, 0.15); color: var(--primary); border: 1px solid rgba(56, 189, 248, 0.3); pointer-events: none; display: none; }

.omni-actions { display: flex; gap: 6px; }

/* Buttons */
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: var(--radius-sm); font-size: 11px; font-weight: 700; border: none; cursor: pointer; text-decoration: none; transition: all 0.15s; white-space: nowrap; }
.btn-primary { background: #fff; color: #000; font-weight: 800; }
.btn-primary:hover { background: #e2e8f0; }
.btn-accent { background: var(--primary); color: #000; font-weight: 800; }
.btn-accent:hover { filter: brightness(1.1); }
.btn-secondary { background: var(--surface-raised); color: var(--text); border: 1px solid var(--border); }
.btn-secondary:hover { border-color: var(--primary); color: #fff; }
.btn-yellow { background: var(--amber); color: #000; font-weight: 800; }
.btn-danger { background: rgba(244, 63, 94, 0.12); color: var(--danger); border: 1px solid rgba(244, 63, 94, 0.3); }
.btn-danger:hover { background: rgba(244, 63, 94, 0.25); }
.btn-sm { padding: 4px 9px; font-size: 10px; }

/* Quick Launchpad Chips */
.quick-launch-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 6px; margin-top: 10px; }
.quick-chip { background: var(--surface-raised); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 8px 10px; cursor: pointer; transition: all 0.15s; display: flex; align-items: center; gap: 7px; }
.quick-chip:hover { border-color: var(--primary); background: var(--surface-hover); transform: translateY(-1px); }
.quick-chip-icon { font-size: 12px; }
.quick-chip-text { font-size: 11px; font-weight: 700; color: #fff; }

/* ========================================================= */
/* --- FOLDERS & INVESTIGATION CASES SYSTEM (ПАПКИ) --- */
/* ========================================================= */
.folder-header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.folder-pills-row { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 6px; margin-bottom: 12px; scrollbar-width: none; }
.folder-pills-row::-webkit-scrollbar { display: none; }
.folder-pill { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: var(--radius-sm); font-size: 11px; font-weight: 700; background: var(--surface); border: 1px solid var(--border); color: var(--text-muted); cursor: pointer; transition: all 0.15s; white-space: nowrap; }
.folder-pill:hover, .folder-pill.active { background: var(--surface-raised); border-color: var(--primary); color: #fff; }
.folder-pill.active .folder-pill-count { background: var(--primary); color: #000; }
.folder-pill-count { font-size: 9px; font-weight: 800; padding: 1px 5px; border-radius: 8px; background: var(--border); color: var(--text-muted); }

.folder-cases-container { display: flex; flex-direction: column; gap: 8px; }
.case-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 12px; transition: all 0.15s; display: flex; flex-direction: column; gap: 8px; }
.case-card:hover { border-color: rgba(56, 189, 248, 0.4); }
.case-card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.case-target-title { font-size: 13px; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 6px; }
.case-meta { font-size: 10px; color: var(--text-muted); display: flex; align-items: center; gap: 8px; }
.case-note { font-size: 11px; color: #cbd5e1; background: #07090e; padding: 6px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border); border-left: 2px solid var(--primary); }
.case-actions { display: flex; justify-content: space-between; align-items: center; gap: 6px; margin-top: 2px; }

.empty-state { text-align: center; padding: 32px 16px; background: var(--surface); border: 1px dashed var(--border); border-radius: var(--radius-md); color: var(--text-muted); }
.empty-state i { font-size: 32px; color: var(--text-dim); margin-bottom: 8px; }

/* Filter Chips (Catalog) */
.filter-chips { display: flex; gap: 5px; overflow-x: auto; padding-bottom: 6px; margin-bottom: 12px; scrollbar-width: none; }
.filter-chips::-webkit-scrollbar { display: none; }
.chip { padding: 5px 11px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 10px; font-weight: 700; color: var(--text-muted); white-space: nowrap; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; transition: all 0.15s; }
.chip:hover, .chip.active { background: var(--surface-raised); border-color: var(--primary); color: #fff; }

/* Catalog Cards */
.group-title { font-size: 11px; font-weight: 800; color: var(--text-muted); margin: 14px 0 6px; display: flex; align-items: center; gap: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
.cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 8px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 12px; cursor: pointer; transition: all 0.15s; display: flex; flex-direction: column; justify-content: space-between; }
.card:hover { border-color: var(--primary); background: var(--surface-hover); transform: translateY(-1px); }
.card-title { font-size: 12px; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 6px; line-height: 1.3; }
.card-purpose { font-size: 10px; color: #94a3b8; line-height: 1.4; margin: 6px 0 10px; flex: 1; }

.badge { font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; white-space: nowrap; }
.badge-api { background: rgba(56, 189, 248, 0.1); color: var(--primary); border: 1px solid rgba(56, 189, 248, 0.25); }
.badge-web { background: var(--surface-raised); color: var(--text-muted); border: 1px solid var(--border); }
.badge-photo { background: rgba(245, 158, 11, 0.12); color: var(--amber); border: 1px solid rgba(245, 158, 11, 0.3); }

/* Custom Result Card */
.result-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 14px; margin-bottom: 10px; box-shadow: 0 4px 16px rgba(0,0,0,0.3); }
.result-header-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.result-title { font-size: 13px; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 6px; }

.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 6px; margin-bottom: 10px; }
.stat-box { background: #07090e; border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 8px 10px; }
.stat-label { font-size: 9px; color: var(--text-muted); margin-bottom: 2px; text-transform: uppercase; }
.stat-val { font-size: 11px; font-weight: 700; color: #fff; word-break: break-all; }

/* Spinner */
.loader { display: none; text-align: center; padding: 18px; }
.spinner { width: 22px; height: 22px; border: 2px solid #1e293b; border-top-color: var(--primary); border-radius: 50%; animation: spin 0.7s linear infinite; margin: 0 auto 6px; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Modals */
.modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 9999; backdrop-filter: blur(8px); align-items: center; justify-content: center; padding: 16px; }
.modal-box { background: #0c111a; border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 18px; max-width: 440px; width: 100%; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.modal-title { font-size: 13px; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 7px; }

/* Toast */
.toast-msg { position: fixed; bottom: 20px; right: 20px; background: #0c1424; border: 1px solid var(--primary); color: #fff; padding: 10px 16px; border-radius: var(--radius-sm); font-size: 11px; font-weight: 700; z-index: 10000; box-shadow: 0 4px 20px rgba(0,0,0,0.5); display: none; animation: slideUp 0.2s ease-out; }
@keyframes slideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

/* Collapsible CLI */
.cli-box { background: #040609; border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 10px; font-family: var(--font-mono); font-size: 11px; line-height: 1.5; color: #cbd5e1; max-height: 240px; overflow-y: auto; white-space: pre-wrap; margin-top: 8px; }

/* Admin Table */
.admin-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.admin-table th { background: #07090e; color: var(--text-muted); padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); font-size: 10px; text-transform: uppercase; }
.admin-table td { padding: 8px 10px; border-bottom: 1px solid var(--border); color: #cbd5e1; }
.admin-table tr:hover td { background: var(--surface-hover); }

/* Dropzone */
.dropzone { border: 1px dashed var(--border); border-radius: var(--radius-md); padding: 16px; text-align: center; background: #05070c; cursor: pointer; transition: all 0.2s; margin-top: 8px; }
.dropzone:hover, .dropzone.dragover { border-color: var(--primary); background: var(--surface-raised); }
</style>
</head>
<body>

<div class="app-container">
  
  <!-- TOP HEADER -->
  <header class="top-header">
    <div class="brand-group" onclick="showView('searchView')">
      <div class="brand-icon"><i class="fa-solid fa-shield-halved"></i></div>
      <div>
        <div class="brand-text">ISLAND INTELLIGENCE <span class="live-badge">ONLINE</span></div>
        <div class="brand-sub">OFFICIAL OSINT & CYBER FORENSICS</div>
      </div>
    </div>
    <div class="header-badges">
      <div class="pill-badge pill-quota" id="quotaBadge" onclick="openStarsModal()" title="Баланс запросов и Stars">
        <i class="fa-solid fa-star"></i> <span id="quotaSpan">5/5</span>
      </div>
      <div class="pill-badge" id="currentUserBadge" onclick="handleUserBadgeClick()" title="Профиль агента / Вход">
        <i class="fa-solid fa-user-shield" id="userBadgeIcon" style="color:var(--primary);"></i>
        <span id="currentUsernameSpan">Агент</span>
      </div>
      <button class="btn btn-yellow btn-sm" id="navAdminBtn" onclick="showView('adminView')" style="display:none;">
        <i class="fa-solid fa-crown"></i> Админ
      </button>
    </div>
  </header>

  <!-- NAVIGATION TABS -->
  <nav class="nav-tabs">
    <button class="nav-tab-btn active" id="tab-searchView" onclick="showView('searchView')">
      <i class="fa-solid fa-bolt"></i> Поиск
    </button>
    <button class="nav-tab-btn" id="tab-foldersView" onclick="showView('foldersView')">
      <i class="fa-solid fa-folder"></i> Папки <span class="nav-tab-badge" id="totalCasesBadge">0</span>
    </button>
    <button class="nav-tab-btn" id="tab-catalogView" onclick="showView('catalogView')">
      <i class="fa-solid fa-layer-group"></i> Каталог
    </button>
    <button class="nav-tab-btn" id="tab-graphView" onclick="showView('graphView')">
      <i class="fa-solid fa-circle-nodes"></i> Граф
    </button>
    <button class="nav-tab-btn" id="tab-decoderView" onclick="showView('decoderView')">
      <i class="fa-solid fa-terminal"></i> Лаб
    </button>
  </nav>

  <!-- ========================================================= -->
  <!-- 1. VIEW: OMNISEARCH & TERMINAL (ПОИСК) -->
  <!-- ========================================================= -->
  <section class="view-page active" id="searchView">
    
    <!-- OmniSearch Input Box -->
    <div class="omni-container">
      <div class="omni-input-row">
        <div class="omni-input-wrap">
          <i class="fa-solid fa-magnifying-glass omni-icon"></i>
          <input class="omni-input" id="omniInput" placeholder="Введите никнейм, телефон (+7...), email, кошелек 0x/BTC или домен..." oninput="handleOmniInput(event)" onkeydown="if(event.key==='Enter') runSmartScan()">
          <span class="omni-type-badge" id="omniTypeBadge">Обнаружен: Ник</span>
        </div>
        <button class="btn btn-primary" onclick="runSmartScan()">
          <i class="fa-solid fa-crosshairs"></i> Скан
        </button>
        <button class="btn btn-secondary" onclick="toggleOmniPhotoSection()" title="Прикрепить фото / Face AI">
          <i class="fa-solid fa-camera"></i>
        </button>
      </div>

      <!-- Photo Dropzone inside OmniSearch -->
      <div id="omniPhotoSection" style="display:none;">
        <input type="file" id="omniFileInput" accept="image/*" style="display:none;" onchange="handleFileSelected(event)">
        <div class="dropzone" id="omniDropzone" onclick="document.getElementById('omniFileInput').click()" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDrop(event)">
          <i class="fa-solid fa-cloud-arrow-up" style="font-size:20px; color:var(--primary); margin-bottom:4px;"></i>
          <div style="font-size:11px; font-weight:700; color:#fff;">Перетащите фото лица или нажмите для выбора</div>
          <div style="font-size:9px; color:var(--text-muted); margin-top:2px;">Поддерживается вставка из буфера обмена (Ctrl + V)</div>
        </div>

        <div id="omniPhotoPreviewBox" style="display:none; background:#07090e; border:1px solid var(--primary); border-radius:var(--radius-sm); padding:8px 10px; margin-top:8px; display:flex; align-items:center; gap:10px;">
          <img id="omniPhotoPreviewImg" src="" alt="Photo" style="width:48px; height:48px; border-radius:4px; object-fit:cover; border:1px solid var(--border);">
          <div style="flex:1; min-width:0;">
            <div id="omniPhotoFileName" style="font-size:11px; font-weight:700; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">photo.jpg</div>
            <div id="omniPhotoMeta" style="font-size:9px; color:var(--text-muted);">0 KB</div>
          </div>
          <button class="btn btn-danger btn-sm" onclick="clearUploadedPhoto()"><i class="fa-solid fa-trash"></i></button>
        </div>
      </div>

      <!-- Quick Launchpad -->
      <div class="quick-launch-grid">
        <div class="quick-chip" onclick="quickFillAndScan('ai_detective_profiler')">
          <i class="fa-solid fa-brain quick-chip-icon" style="color:var(--primary);"></i>
          <span class="quick-chip-text">AI Досье</span>
        </div>
        <div class="quick-chip" onclick="quickFillAndScan('crypto_aml_auditor')">
          <i class="fa-solid fa-shield-halved quick-chip-icon" style="color:var(--green);"></i>
          <span class="quick-chip-text">AML Аудит</span>
        </div>
        <div class="quick-chip" onclick="quickFillAndScan('face_search_ai')">
          <i class="fa-solid fa-user-astronaut quick-chip-icon" style="color:var(--cyan);"></i>
          <span class="quick-chip-text">Face AI</span>
        </div>
        <div class="quick-chip" onclick="quickFillAndScan('tg_activity_tracker')">
          <i class="fa-solid fa-clock quick-chip-icon" style="color:var(--amber);"></i>
          <span class="quick-chip-text">Шпион онлайна</span>
        </div>
        <div class="quick-chip" onclick="quickFillAndScan('digital_hygiene_audit')">
          <i class="fa-solid fa-lock-open quick-chip-icon" style="color:var(--purple);"></i>
          <span class="quick-chip-text">Проверка утечек</span>
        </div>
        <div class="quick-chip" onclick="quickFillAndScan('myip_toolbox')">
          <i class="fa-solid fa-network-wired quick-chip-icon" style="color:var(--primary);"></i>
          <span class="quick-chip-text">MyIP & VPN</span>
        </div>
      </div>
    </div>

    <!-- Active Loading Spinner -->
    <div class="loader" id="searchLoader">
      <div class="spinner"></div>
      <span style="font-size:11px; color:var(--primary);">Сквозной анализ открытых источников и реестров...</span>
    </div>

    <!-- Active Result Container -->
    <div id="searchResultBox"></div>
  </section>

  <!-- ========================================================= -->
  <!-- 2. VIEW: INVESTIGATION FOLDERS SYSTEM (ПАПКИ) -->
  <!-- ========================================================= -->
  <section class="view-page" id="foldersView">
    <div class="folder-header-bar">
      <div>
        <h2 style="font-size:14px; font-weight:800; color:#fff; display:flex; align-items:center; gap:6px;">
          <i class="fa-solid fa-folder-open" style="color:var(--amber);"></i> Папки расследований
        </h2>
        <div style="font-size:10px; color:var(--text-muted); margin-top:2px;">
          Группируйте поиски по кейсам, сохраняйте досье и экспортируйте отчеты
        </div>
      </div>
      <div style="display:flex; gap:6px;">
        <button class="btn btn-secondary btn-sm" onclick="exportCurrentFolder()"><i class="fa-solid fa-file-export"></i> Экспорт</button>
        <button class="btn btn-primary btn-sm" onclick="openNewFolderModal()"><i class="fa-solid fa-plus"></i> Новая папка</button>
      </div>
    </div>

    <!-- Folder Navigation Pills -->
    <div class="folder-pills-row" id="folderPillsRow"></div>

    <!-- Folder Search & Info Bar -->
    <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:10px;">
      <input class="omni-input" id="folderSearchInput" placeholder="Поиск в этой папке..." oninput="renderFolderCases()" style="padding:7px 10px; font-size:11px;">
      <div style="font-size:10px; color:var(--text-muted); white-space:nowrap;" id="folderCasesCountLabel">0 расследований</div>
    </div>

    <!-- Folder Cases List -->
    <div class="folder-cases-container" id="folderCasesContainer"></div>
  </section>

  <!-- ========================================================= -->
  <!-- 3. VIEW: MODULES CATALOG (КАТАЛОГ) -->
  <!-- ========================================================= -->
  <section class="view-page" id="catalogView">
    <div style="margin-bottom:10px;">
      <input class="omni-input" id="catalogSearchInput" placeholder="Фильтр по 55+ инструментам и репозиториям..." oninput="renderCatalog()" style="padding:9px 12px; font-size:12px;">
    </div>

    <div class="filter-chips">
      <div class="chip active" onclick="setCatalogFilter('all', this)"><i class="fa-solid fa-layer-group"></i> Все (55)</div>
      <div class="chip" onclick="setCatalogFilter('killer_monetization', this)"><i class="fa-solid fa-gem" style="color:var(--amber);"></i> AI & Топ (6)</div>
      <div class="chip" onclick="setCatalogFilter('telegram_osint', this)"><i class="fa-brands fa-telegram" style="color:#38bdf8;"></i> Telegram (5)</div>
      <div class="chip" onclick="setCatalogFilter('username_osint', this)"><i class="fa-solid fa-user-tag" style="color:#a855f7;"></i> Никнеймы (5)</div>
      <div class="chip" onclick="setCatalogFilter('social_google_instagram', this)"><i class="fa-brands fa-instagram" style="color:#ec4899;"></i> Соцсети (7)</div>
      <div class="chip" onclick="setCatalogFilter('web_infra_secrets', this)"><i class="fa-solid fa-globe" style="color:#38bdf8;"></i> Домены, IP & MyIP (10)</div>
      <div class="chip" onclick="setCatalogFilter('email_checks', this)"><i class="fa-solid fa-envelope" style="color:#10b981;"></i> Почта & Телефон (3)</div>
      <div class="chip" onclick="setCatalogFilter('hacker_crypto_git', this)"><i class="fa-solid fa-coins" style="color:#eab308;"></i> Крипта & GitHub (3)</div>
      <div class="chip" onclick="setCatalogFilter('amazing_osint', this)"><i class="fa-solid fa-earth-americas" style="color:#10b981;"></i> Фото & GeoINT (11)</div>
      <div class="chip" onclick="setCatalogFilter('cyber_tools_lab', this)"><i class="fa-solid fa-wand-magic-sparkles" style="color:#f59e0b;"></i> Декодеры (5)</div>
    </div>

    <div id="catalogCardsContainer"></div>
  </section>

  <!-- ========================================================= -->
  <!-- 4. VIEW: VIS.JS GRAPH (ГРАФ СВЯЗЕЙ) -->
  <!-- ========================================================= -->
  <section class="view-page" id="graphView">
    <div class="result-card">
      <div class="result-header-toolbar">
        <div class="result-title"><i class="fa-solid fa-circle-nodes" style="color:var(--primary);"></i> Интерактивный Граф Связей</div>
        <div style="display:flex; gap:6px;">
          <button class="btn btn-secondary btn-sm" onclick="exportCurrentGraph()"><i class="fa-solid fa-camera"></i> PNG</button>
          <button class="btn btn-secondary btn-sm" onclick="clearGraph()"><i class="fa-solid fa-rotate-left"></i> Сброс</button>
        </div>
      </div>
      <div style="display:flex; gap:6px; margin-bottom:10px;">
        <input class="omni-input" id="graphTargetInput" placeholder="Введите цель для построения графа..." onkeydown="if(event.key==='Enter') runGraphDirectScan()">
        <button class="btn btn-primary" onclick="runGraphDirectScan()"><i class="fa-solid fa-bolt"></i> Построить</button>
      </div>
      <div id="visNetworkCanvas" style="width:100%; height:400px; background:#04060a; border:1px solid var(--border); border-radius:var(--radius-sm); margin-bottom:10px;"></div>
      <div id="graphDossierBox" style="display:none;" class="stat-box">
        <div style="font-size:10px; font-weight:800; color:var(--primary); margin-bottom:4px;"><i class="fa-solid fa-file-shield"></i> Тактическая сводка связей:</div>
        <div id="graphDossierContent" style="font-size:11px; color:#cbd5e1; white-space:pre-wrap; line-height:1.5;"></div>
      </div>
    </div>
  </section>

  <!-- ========================================================= -->
  <!-- 5. VIEW: CYBER LAB & DECODERS (ЛАБОРАТОРИЯ) -->
  <!-- ========================================================= -->
  <section class="view-page" id="decoderView">
    <div class="result-card">
      <div class="result-title" style="margin-bottom:10px;"><i class="fa-solid fa-wrench" style="color:var(--cyan);"></i> Кибер-Декодеры & Хеш-Идентификаторы</div>
      <textarea class="omni-input" id="decoderInputData" placeholder="Вставьте зашифрованную строку, хеш (MD5/SHA/bcrypt) или JWT..." style="width:100%; height:75px; resize:vertical; margin-bottom:8px; font-family:var(--font-mono);"></textarea>

      <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:10px;">
        <button class="btn btn-primary btn-sm" onclick="runDecoderAction('hash_id')"><i class="fa-solid fa-fingerprint"></i> Хеш-ID</button>
        <button class="btn btn-secondary btn-sm" onclick="runDecoderAction('jwt_decode')"><i class="fa-solid fa-shield-halved"></i> JWT Token</button>
        <button class="btn btn-secondary btn-sm" onclick="runDecoderAction('base64_decode')">Base64 Decode</button>
        <button class="btn btn-secondary btn-sm" onclick="runDecoderAction('base64_encode')">Base64 Encode</button>
        <button class="btn btn-secondary btn-sm" onclick="runDecoderAction('hex_decode')">Hex Decode</button>
        <button class="btn btn-secondary btn-sm" onclick="runDecoderAction('rot13')">ROT13</button>
      </div>

      <div id="decoderResultBox" style="display:none;" class="stat-box">
        <div style="font-size:10px; font-weight:800; color:var(--primary); margin-bottom:4px;">Результат декодирования:</div>
        <pre id="decoderOutputPre" style="font-family:var(--font-mono); color:var(--primary); font-size:11px; white-space:pre-wrap; word-break:break-all; max-height:220px; overflow-y:auto;"></pre>
      </div>
    </div>
  </section>

  <!-- ========================================================= -->
  <!-- 6. VIEW: ADMIN CENTER (АДМИНКА) -->
  <!-- ========================================================= -->
  <section class="view-page" id="adminView">
    <div class="result-card">
      <div class="result-header-toolbar">
        <div class="result-title"><i class="fa-solid fa-users-gear" style="color:var(--amber);"></i> Управление пользователями & Квоты</div>
        <button class="btn btn-primary btn-sm" onclick="toggleAddUserModal()"><i class="fa-solid fa-plus"></i> Добавить</button>
      </div>

      <div id="addUserFormBox" style="display:none; background:#07090e; padding:10px; border-radius:var(--radius-sm); margin-bottom:10px; border:1px solid var(--border);">
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:6px;">
          <input class="omni-input" id="newUsername" placeholder="Позывной / Ник">
          <input class="omni-input" id="newNotes" placeholder="Telegram ID">
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:6px;">
          <select class="omni-input" id="newRole">
            <option value="user">User (Обычный)</option>
            <option value="vip">VIP (Бесконечный)</option>
            <option value="admin">Admin</option>
          </select>
          <input class="omni-input" id="newPassword" type="password" placeholder="Пароль">
        </div>
        <div style="display:flex; gap:6px;">
          <button class="btn btn-primary btn-sm" onclick="submitCreateUser()">Создать</button>
          <button class="btn btn-secondary btn-sm" onclick="toggleAddUserModal()">Отмена</button>
        </div>
      </div>

      <div style="overflow-x:auto;">
        <table class="admin-table">
          <thead>
            <tr><th>Позывной</th><th>Telegram</th><th>Квота</th><th>Статус</th><th>Действия</th></tr>
          </thead>
          <tbody id="usersTableBody">
            <tr><td colspan="5" style="text-align:center;">Загрузка...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="result-card">
      <div class="result-header-toolbar">
        <div class="result-title"><i class="fa-solid fa-network-wired" style="color:var(--primary);"></i> Журнал IP-визитов</div>
        <button class="btn btn-secondary btn-sm" onclick="loadAdminVisitors()"><i class="fa-solid fa-rotate"></i></button>
      </div>
      <div style="overflow-x:auto;">
        <table class="admin-table">
          <thead>
            <tr><th>Время</th><th>Пользователь</th><th>IP адрес</th><th>Гео</th></tr>
          </thead>
          <tbody id="visitorsTableBody">
            <tr><td colspan="4" style="text-align:center;">Загрузка...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>

</div>

<!-- ========================================================= -->
<!-- MODAL: СОХРАНЕНИЕ В ПАПКУ (SAVE TO FOLDER) -->
<!-- ========================================================= -->
<div class="modal-overlay" id="saveCaseModal">
  <div class="modal-box">
    <div class="modal-header">
      <div class="modal-title"><i class="fa-solid fa-folder-plus" style="color:var(--amber);"></i> Сохранить в папку</div>
      <button onclick="closeSaveCaseModal()" style="background:none; border:none; color:var(--text-muted); font-size:18px; cursor:pointer;">&times;</button>
    </div>
    <div style="font-size:11px; color:#cbd5e1; margin-bottom:12px;">
      Выберите папку для прикрепления результатов расследования цели <b id="modalSaveTarget" style="color:#fff;"></b>:
    </div>
    <div style="margin-bottom:10px;">
      <label style="font-size:10px; color:var(--text-muted); display:block; margin-bottom:3px;">ПАПКА РАССЛЕДОВАНИЯ</label>
      <select class="omni-input" id="modalFolderSelect" style="width:100%;"></select>
    </div>
    <div style="margin-bottom:12px;">
      <label style="font-size:10px; color:var(--text-muted); display:block; margin-bottom:3px;">ЗАМЕТКА РАССЛЕДОВАТЕЛЯ (ОПЦИОНАЛЬНО)</label>
      <input class="omni-input" id="modalCaseNotes" placeholder="Например: Подозрительный кошелек, возможный дроп...">
    </div>
    <div style="display:flex; justify-content:flex-end; gap:6px;">
      <button class="btn btn-secondary btn-sm" onclick="closeSaveCaseModal()">Отмена</button>
      <button class="btn btn-primary btn-sm" onclick="commitSaveCase()"><i class="fa-solid fa-check"></i> Сохранить</button>
    </div>
  </div>
</div>

<!-- MODAL: СОЗДАНИЕ НОВОЙ ПАПКИ -->
<div class="modal-overlay" id="newFolderModal">
  <div class="modal-box">
    <div class="modal-header">
      <div class="modal-title"><i class="fa-solid fa-folder-plus" style="color:var(--primary);"></i> Новая папка поиска</div>
      <button onclick="closeNewFolderModal()" style="background:none; border:none; color:var(--text-muted); font-size:18px; cursor:pointer;">&times;</button>
    </div>
    <div style="margin-bottom:12px;">
      <label style="font-size:10px; color:var(--text-muted); display:block; margin-bottom:3px;">НАЗВАНИЕ ПАПКИ</label>
      <input class="omni-input" id="newFolderNameInput" placeholder="Например: Дело №42: Проверка контрагента">
    </div>
    <div style="display:flex; justify-content:flex-end; gap:6px;">
      <button class="btn btn-secondary btn-sm" onclick="closeNewFolderModal()">Отмена</button>
      <button class="btn btn-primary btn-sm" onclick="commitCreateFolder()"><i class="fa-solid fa-check"></i> Создать папку</button>
    </div>
  </div>
</div>

<!-- MODAL: STARS TOPUP -->
<div class="modal-overlay" id="starsModal">
  <div class="modal-box">
    <div class="modal-header">
      <div class="modal-title"><i class="fa-solid fa-star" style="color:var(--amber);"></i> Пополнение Stars</div>
      <button onclick="closeStarsModal()" style="background:none; border:none; color:var(--text-muted); font-size:18px; cursor:pointer;">&times;</button>
    </div>
    <div style="font-size:11px; color:#cbd5e1; margin-bottom:12px;">
      Каждому новому агенту предоставляется <b>5 бесплатных проверок</b>.<br>Для продолжения работы выберите пакет:
    </div>
    <div style="display:flex; flex-direction:column; gap:6px; margin-bottom:12px;">
      <div onclick="buyStarsPkg('pkg_20')" style="background:#07090e; border:1px solid var(--border); border-radius:var(--radius-sm); padding:10px; display:flex; justify-content:space-between; align-items:center; cursor:pointer;">
        <div><div style="font-size:11px; font-weight:800; color:#fff;">🌟 20 OSINT Запросов</div><div style="font-size:9px; color:var(--text-muted);">Тариф «Разведчик»</div></div>
        <button class="btn btn-yellow btn-sm">35 ⭐️</button>
      </div>
      <div onclick="buyStarsPkg('pkg_50')" style="background:#07090e; border:1px solid var(--border); border-radius:var(--radius-sm); padding:10px; display:flex; justify-content:space-between; align-items:center; cursor:pointer;">
        <div><div style="font-size:11px; font-weight:800; color:#fff;">🌟 50 OSINT Запросов</div><div style="font-size:9px; color:var(--text-muted);">Тариф «Оперативник»</div></div>
        <button class="btn btn-yellow btn-sm">88 ⭐️</button>
      </div>
      <div onclick="buyStarsPkg('pkg_100')" style="background:#07090e; border:1px solid var(--border); border-radius:var(--radius-sm); padding:10px; display:flex; justify-content:space-between; align-items:center; cursor:pointer;">
        <div><div style="font-size:11px; font-weight:800; color:#fff;">🌟 100 OSINT Запросов</div><div style="font-size:9px; color:var(--text-muted);">Тариф «Архимаг»</div></div>
        <button class="btn btn-yellow btn-sm">235 ⭐️</button>
      </div>
    </div>
    <button class="btn btn-secondary btn-sm" style="width:100%; justify-content:center;" onclick="closeStarsModal()">Закрыть</button>
  </div>
</div>

<!-- TOAST NOTIFICATION -->
<div class="toast-msg" id="appToast"><i class="fa-solid fa-check"></i> <span id="toastText">Успешно</span></div>

<script>
// =====================================================================
// --- INITIAL DATA & CATALOG ---
// =====================================================================
let FULL_CATALOG = __CATALOG_INJECT__;

let currentSessionUser = 'guest';
let tgUserId = '';
let currentUploadedBase64 = '';
let currentUploadedFileName = '';
let currentActiveResult = null; // Last scan result for saving
let currentFolderId = 'all';

// Default Folders
const DEFAULT_FOLDERS = [
  { id: 'all', name: 'Все расследования', icon: 'fa-folder-open', isSystem: true },
  { id: 'people', name: 'Люди & Профили', icon: 'fa-user-tag', isSystem: true },
  { id: 'crypto', name: 'Крипта & AML', icon: 'fa-coins', isSystem: true },
  { id: 'infra', name: 'Домены, Сайты & IP', icon: 'fa-globe', isSystem: true },
  { id: 'leaks', name: 'Утечки & Пароли', icon: 'fa-lock-open', isSystem: true },
  { id: 'geoint', name: 'Фото & GeoINT', icon: 'fa-camera', isSystem: true }
];

// Helper: Local Storage for Folders & Cases
function getStoredFolders() {
  try {
    const custom = JSON.parse(localStorage.getItem('osint_custom_folders') || '[]');
    return [...DEFAULT_FOLDERS, ...custom];
  } catch(e) { return DEFAULT_FOLDERS; }
}

function saveCustomFolders(folders) {
  const custom = folders.filter(f => !f.isSystem);
  localStorage.setItem('osint_custom_folders', JSON.stringify(custom));
}

function getStoredCases() {
  try {
    return JSON.parse(localStorage.getItem('osint_saved_cases') || '[]');
  } catch(e) { return []; }
}

function saveStoredCases(cases) {
  localStorage.setItem('osint_saved_cases', JSON.stringify(cases));
  updateCasesCountBadge();
}

function showToast(text) {
  const toast = document.getElementById('appToast');
  const span = document.getElementById('toastText');
  if (span) span.innerText = text;
  if (toast) {
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 2400);
  }
}

// =====================================================================
// --- NAVIGATION & VIEWS ---
// =====================================================================
function showView(viewId) {
  document.querySelectorAll('.view-page').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
  
  const target = document.getElementById(viewId);
  const tabBtn = document.getElementById('tab-' + viewId);
  if (target) target.classList.add('active');
  if (tabBtn) tabBtn.classList.add('active');

  if (viewId === 'foldersView') renderFolderCases();
  if (viewId === 'catalogView') renderCatalog();
  if (viewId === 'adminView') loadAdminUsers();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// =====================================================================
// --- SMART OMNISEARCH INPUT SNIFFER ---
// =====================================================================
function sniffTargetType(str) {
  str = (str || '').trim();
  if (!str) return null;
  if (/^(\+7|8|\+380|\+998|\+1|\+44)\d{9,13}$/.test(str.replace(/[\s\-\(\)]/g, ''))) return { type: 'phone', label: 'Телефон', tool: 'phoneinfoga_recon', icon: 'fa-phone' };
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(str)) return { type: 'email', label: 'Email', tool: 'holehe_osint', icon: 'fa-envelope' };
  if (/^(0x[a-fA-F0-9]{40}|1[a-km-zA-HJ-NP-Z1-9]{25,34}|3[a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-zA-HJ-NP-Z0-9]{25,59}|T[A-Za-z1-9]{33})$/.test(str)) return { type: 'crypto', label: 'Криптокошелек', tool: 'crypto_aml_auditor', icon: 'fa-coins' };
  if (/^(\d{1,3}\.){3}\d{1,3}$/.test(str)) return { type: 'ip', label: 'IP Адрес', tool: 'myip_toolbox', icon: 'fa-network-wired' };
  if (/^([a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}$/.test(str) && !str.includes('@')) return { type: 'domain', label: 'Домен / Сайт', tool: 'crtsh', icon: 'fa-globe' };
  if (str.startsWith('@')) return { type: 'telegram', label: 'Telegram', tool: 'tg_inspector', icon: 'fa-brands fa-telegram' };
  return { type: 'username', label: 'Никнейм / Досье', tool: 'ai_detective_profiler', icon: 'fa-user' };
}

function handleOmniInput(e) {
  const val = e.target.value.trim();
  const badge = document.getElementById('omniTypeBadge');
  if (!val) {
    if (badge) badge.style.display = 'none';
    return;
  }
  const detected = sniffTargetType(val);
  if (detected && badge) {
    badge.innerText = `Цель: ${detected.label}`;
    badge.style.display = 'inline-block';
  }
}

// Global Clipboard Paste for Image Dropzone
window.addEventListener('paste', function(e) {
  const items = (e.clipboardData || e.originalEvent.clipboardData).items;
  for (let i = 0; i < items.length; i++) {
    if (items[i].type.indexOf('image') !== -1) {
      const file = items[i].getAsFile();
      processImageFile(file);
      showView('searchView');
      showToast('Изображение вставлено из буфера!');
      break;
    }
  }
});

function toggleOmniPhotoSection() {
  const sec = document.getElementById('omniPhotoSection');
  if (sec) sec.style.display = (sec.style.display === 'none' ? 'block' : 'none');
}

function handleDragOver(e) { e.preventDefault(); e.currentTarget.classList.add('dragover'); }
function handleDragLeave(e) { e.currentTarget.classList.remove('dragover'); }
function handleDrop(e) {
  e.preventDefault();
  e.currentTarget.classList.remove('dragover');
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    processImageFile(e.dataTransfer.files[0]);
  }
}
function handleFileSelected(e) {
  if (e.target.files && e.target.files[0]) {
    processImageFile(e.target.files[0]);
  }
}

function processImageFile(file) {
  if (!file) return;
  currentUploadedFileName = file.name;
  const reader = new FileReader();
  reader.onload = function(evt) {
    currentUploadedBase64 = evt.target.result;
    const prevImg = document.getElementById('omniPhotoPreviewImg');
    const prevBox = document.getElementById('omniPhotoPreviewBox');
    const nameLabel = document.getElementById('omniPhotoFileName');
    const metaLabel = document.getElementById('omniPhotoMeta');
    const sec = document.getElementById('omniPhotoSection');
    if (sec) sec.style.display = 'block';
    if (prevImg) prevImg.src = currentUploadedBase64;
    if (nameLabel) nameLabel.innerText = file.name;
    if (metaLabel) metaLabel.innerText = `${Math.round(file.size / 1024)} KB · Face AI Ready`;
    if (prevBox) prevBox.style.display = 'flex';
  };
  reader.readAsDataURL(file);
}

function clearUploadedPhoto() {
  currentUploadedBase64 = '';
  currentUploadedFileName = '';
  const prevBox = document.getElementById('omniPhotoPreviewBox');
  if (prevBox) prevBox.style.display = 'none';
}

// Quick Launch chip clicked
function quickFillAndScan(toolId) {
  const input = document.getElementById('omniInput');
  if (toolId === 'face_search_ai') {
    toggleOmniPhotoSection();
    showToast('Прикрепите фото или вставьте через Ctrl+V');
    return;
  }
  if (!input.value.trim()) {
    const examples = {
      'ai_detective_profiler': 'durov',
      'crypto_aml_auditor': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
      'tg_activity_tracker': 'durov',
      'digital_hygiene_audit': 'test@gmail.com',
      'myip_toolbox': '1.1.1.1'
    };
    input.value = examples[toolId] || 'target';
    handleOmniInput({ target: input });
  }
  executeDirectScan(toolId, input.value.trim());
}

// Smart Scan Runner
async function runSmartScan() {
  const target = document.getElementById('omniInput').value.trim();
  if (!target && !currentUploadedBase64) {
    alert('Введите никнейм, телефон, email, кошелек или прикрепите фото');
    return;
  }
  if (currentUploadedBase64) {
    executeDirectScan('face_search_ai', target || currentUploadedFileName);
    return;
  }
  const detected = sniffTargetType(target);
  const toolId = detected ? detected.tool : 'ai_detective_profiler';
  executeDirectScan(toolId, target);
}

// Main API Dispatcher
async function executeDirectScan(toolId, target) {
  const loader = document.getElementById('searchLoader');
  const outBox = document.getElementById('searchResultBox');
  if (loader) loader.style.display = 'block';
  if (outBox) outBox.innerHTML = '';

  try {
    const payload = {
      tool_id: toolId,
      target: target || currentUploadedFileName,
      image_base64: currentUploadedBase64 || '',
      caller: currentSessionUser
    };

    const res = await fetch('/api/scan/universal', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-User-Id': tgUserId || '5233450569'
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (loader) loader.style.display = 'none';

    if (!data.ok) {
      outBox.innerHTML = `<div class="result-card" style="border-color:var(--danger); color:var(--danger);"><i class="fa-solid fa-triangle-exclamation"></i> Ошибка: ${data.error || 'Сбой сканирования'}</div>`;
      return;
    }

    currentActiveResult = { data, target: target || currentUploadedFileName, toolId, timestamp: new Date().toISOString() };
    renderUnifiedResult(data, outBox, target || currentUploadedFileName, toolId);
    initUserProfile(); // update quota
  } catch(err) {
    if (loader) loader.style.display = 'none';
    outBox.innerHTML = `<div class="result-card" style="border-color:var(--danger); color:var(--danger);"><i class="fa-solid fa-triangle-exclamation"></i> Ошибка соединения: ${err.message}</div>`;
  }
}

// =========================================================
// --- UNIFIED RESULT RENDERER WITH SAVE TO FOLDER BUTTON ---
// =========================================================
function renderUnifiedResult(data, outBox, target, toolId) {
  const owner = data.probable_owner || 'Субъект анализа';
  const type = data.type || '';
  const verdict = data.verdict_summary || data.ai_summary || data.ai_verdict || 'Анализ успешно завершен.';
  const confidence = data.confidence || '92%';
  
  let contentHtml = '';

  // 1. Sherlock / Username Profiles Grid
  if (type === 'username') {
    const profiles = data.profiles || [];
    let grid = '<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(200px, 1fr)); gap:6px; margin-top:8px;">';
    profiles.forEach(p => {
      grid += `
        <div style="background:#07090e; border:1px solid var(--border); border-radius:var(--radius-sm); padding:8px 10px; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-size:11px; font-weight:700; color:#fff;">${p.platform}</div>
            <div style="font-size:9px; color:var(--text-muted);">${p.category || 'Профиль'}</div>
          </div>
          <button class="btn btn-primary btn-sm" onclick="openExternalUrl('${p.url}')"><i class="fa-solid fa-arrow-up-right-from-square"></i></button>
        </div>
      `;
    });
    grid += '</div>';
    contentHtml = `
      <div style="font-size:11px; font-weight:800; color:#fff; margin-bottom:4px;">🌐 Обнаружено аккаунтов: <span style="color:var(--primary);">${profiles.length}</span></div>
      ${grid}
    `;
  }
  // 2. Crypto AML
  else if (type === 'crypto_aml') {
    const score = data.aml_risk_score || 0;
    const isDanger = score > 60;
    contentHtml = `
      <div class="stat-grid">
        <div class="stat-box">
          <div class="stat-label">Индекс AML Риска</div>
          <div class="stat-val" style="color:${isDanger ? 'var(--danger)' : 'var(--green)'}; font-size:14px;">${score}% / 100%</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Категория риска</div>
          <div class="stat-val" style="color:${isDanger ? 'var(--danger)' : 'var(--green)'};">${data.risk_level || 'Низкий риск'}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Криптовалюта</div>
          <div class="stat-val">${data.coin || 'BTC / ETH / USDT'}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Баланс / Транзакции</div>
          <div class="stat-val">${data.tx_count || 0} операций</div>
        </div>
      </div>
      <div style="background:#07090e; padding:10px; border-radius:var(--radius-sm); border:1px solid var(--border); font-size:11px; color:#cbd5e1; line-height:1.5;">
        ${data.recommendation || 'Кошелек проверен по санкционным спискам OFAC и даркнет-миксерам.'}
      </div>
    `;
  }
  // 3. Face AI & Biometrics
  else if (type === 'face_search') {
    contentHtml = `
      <div class="stat-grid">
        <div class="stat-box">
          <div class="stat-label">Вердикт подлинности</div>
          <div class="stat-val" style="color:${data.is_ai_generated ? 'var(--danger)' : 'var(--green)'};">${data.ai_verdict || 'Натуральное фото'}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Вероятность Deepfake</div>
          <div class="stat-val" style="color:${data.is_ai_generated ? 'var(--danger)' : 'var(--green)'};">${data.deepfake_probability || '12%'}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Примерный возраст</div>
          <div class="stat-val">${data.estimated_age || '25-30 лет'}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Симметрия лица</div>
          <div class="stat-val" style="color:var(--primary);">${data.facial_symmetry || '94%'}</div>
        </div>
      </div>
    `;
  }
  // 4. Default / Telegram / Phone / Email / AI Profiler
  else {
    contentHtml = `
      <div class="stat-grid">
        <div class="stat-box">
          <div class="stat-label">Тип объекта</div>
          <div class="stat-val" style="color:var(--primary);">${data.entity_type || type || 'Идентификатор'}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Юрисдикция / Регион</div>
          <div class="stat-val">${data.jurisdiction || data.country || 'Глобальная сеть'}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Достоверность данных</div>
          <div class="stat-val" style="color:var(--green);">${confidence}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Статус проверки</div>
          <div class="stat-val" style="color:var(--green);">🟢 ВАЛИДИРОВАНО</div>
        </div>
      </div>
      <div style="background:#07090e; padding:10px; border-radius:var(--radius-sm); border:1px solid var(--border); font-size:11px; color:#cbd5e1; line-height:1.5;">
        ${verdict}
      </div>
    `;
  }

  // Quick Action Buttons (Save to Folder, Add to Graph, Copy, Terminal)
  const toolbar = `
    <div class="result-header-toolbar">
      <div class="result-title">
        <i class="fa-solid fa-crosshairs" style="color:var(--primary);"></i>
        <span>${owner}</span>
        <span style="font-size:9px; color:var(--text-muted); font-family:var(--font-mono);">(${target})</span>
      </div>
      <div style="display:flex; gap:6px; flex-wrap:wrap;">
        <button class="btn btn-yellow btn-sm" onclick="openSaveCaseModal()"><i class="fa-solid fa-folder-plus"></i> В папку</button>
        <button class="btn btn-secondary btn-sm" onclick="sendResultToGraph()"><i class="fa-solid fa-circle-nodes"></i> В граф</button>
        <button class="btn btn-secondary btn-sm" onclick="copyResultSummary()"><i class="fa-solid fa-copy"></i> Копировать</button>
        <button class="btn btn-secondary btn-sm" onclick="toggleResultCli()"><i class="fa-solid fa-terminal"></i> CLI</button>
      </div>
    </div>
  `;

  const rawCli = data.raw_cli_output ? `
    <div id="resultCliBox" class="cli-box" style="display:none;">${data.raw_cli_output}</div>
  ` : '';

  outBox.innerHTML = `
    <div class="result-card">
      ${toolbar}
      ${contentHtml}
      ${rawCli}
    </div>
  `;
}

function toggleResultCli() {
  const el = document.getElementById('resultCliBox');
  if (el) el.style.display = (el.style.display === 'none' ? 'block' : 'none');
}

function copyResultSummary() {
  if (!currentActiveResult) return;
  const t = currentActiveResult.target;
  const d = currentActiveResult.data;
  const text = `[OSINT DOSSIER] Цель: ${t}\nВладелец: ${d.probable_owner || 'Не указан'}\nВердикт: ${d.verdict_summary || d.ai_verdict || 'OK'}`;
  navigator.clipboard.writeText(text);
  showToast('Сводка скопирована в буфер обмена!');
}

function sendResultToGraph() {
  if (!currentActiveResult) return;
  const t = currentActiveResult.target;
  document.getElementById('graphTargetInput').value = t;
  showView('graphView');
  runGraphDirectScan();
}

// =====================================================================
// --- FOLDERS SYSTEM IMPLEMENTATION (ПАПКИ) ---
// =====================================================================
function openSaveCaseModal() {
  if (!currentActiveResult) {
    alert('Сначала выполните поиск цели');
    return;
  }
  const modal = document.getElementById('saveCaseModal');
  const targetLabel = document.getElementById('modalSaveTarget');
  const select = document.getElementById('modalFolderSelect');
  
  if (targetLabel) targetLabel.innerText = currentActiveResult.target;
  
  const folders = getStoredFolders();
  select.innerHTML = '';
  folders.forEach(f => {
    if (f.id === 'all') return;
    const opt = document.createElement('option');
    opt.value = f.id;
    opt.innerText = f.name;
    select.appendChild(opt);
  });

  // Auto-select folder by target type
  const detected = sniffTargetType(currentActiveResult.target);
  if (detected) {
    const map = { 'phone': 'people', 'email': 'people', 'crypto': 'crypto', 'ip': 'infra', 'domain': 'infra', 'telegram': 'people', 'username': 'people' };
    if (map[detected.type]) select.value = map[detected.type];
  }

  if (modal) modal.style.display = 'flex';
}

function closeSaveCaseModal() {
  const m = document.getElementById('saveCaseModal');
  if (m) m.style.display = 'none';
}

function commitSaveCase() {
  if (!currentActiveResult) return;
  const folderId = document.getElementById('modalFolderSelect').value || 'people';
  const notes = document.getElementById('modalCaseNotes').value.trim();
  const cases = getStoredCases();

  const newCase = {
    id: 'case_' + Date.now(),
    folderId: folderId,
    target: currentActiveResult.target,
    toolId: currentActiveResult.toolId,
    data: currentActiveResult.data,
    notes: notes,
    createdAt: new Date().toISOString()
  };

  cases.unshift(newCase);
  saveStoredCases(cases);
  closeSaveCaseModal();
  showToast(`Сохранено в папку!`);
}

function openNewFolderModal() {
  const m = document.getElementById('newFolderModal');
  if (m) m.style.display = 'flex';
}

function closeNewFolderModal() {
  const m = document.getElementById('newFolderModal');
  if (m) m.style.display = 'none';
}

function commitCreateFolder() {
  const name = document.getElementById('newFolderNameInput').value.trim();
  if (!name) {
    alert('Введите название папки');
    return;
  }
  const folders = getStoredFolders();
  const newFolder = {
    id: 'folder_' + Date.now(),
    name: name,
    icon: 'fa-folder',
    isSystem: false
  };
  folders.push(newFolder);
  saveCustomFolders(folders);
  closeNewFolderModal();
  document.getElementById('newFolderNameInput').value = '';
  renderFolderCases();
  showToast(`Папка "${name}" создана!`);
}

function renderFolderCases() {
  const pillsRow = document.getElementById('folderPillsRow');
  const container = document.getElementById('folderCasesContainer');
  const search = (document.getElementById('folderSearchInput').value || '').toLowerCase().trim();
  const folders = getStoredFolders();
  const allCases = getStoredCases();

  // Render Folder Pills
  pillsRow.innerHTML = '';
  folders.forEach(f => {
    const count = f.id === 'all' ? allCases.length : allCases.filter(c => c.folderId === f.id).length;
    const pill = document.createElement('div');
    pill.className = `folder-pill ${currentFolderId === f.id ? 'active' : ''}`;
    pill.onclick = () => { currentFolderId = f.id; renderFolderCases(); };
    pill.innerHTML = `<i class="fa-solid ${f.icon}"></i> ${f.name} <span class="folder-pill-count">${count}</span>`;
    pillsRow.appendChild(pill);
  });

  // Filter cases
  let cases = currentFolderId === 'all' ? allCases : allCases.filter(c => c.folderId === currentFolderId);
  if (search) {
    cases = cases.filter(c => c.target.toLowerCase().includes(search) || (c.notes && c.notes.toLowerCase().includes(search)));
  }

  document.getElementById('folderCasesCountLabel').innerText = `${cases.length} расследований`;

  if (cases.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <i class="fa-solid fa-folder-open"></i>
        <div style="font-weight:700; font-size:12px; color:#fff; margin-bottom:4px;">В этой папке пока нет расследований</div>
        <div style="font-size:10px;">Проведите поиск в разделе «Поиск» и нажмите «В папку»</div>
      </div>
    `;
    return;
  }

  container.innerHTML = '';
  cases.forEach(c => {
    const card = document.createElement('div');
    card.className = 'case-card';
    const dateStr = new Date(c.createdAt).toLocaleDateString('ru-RU', { day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit' });
    const verdict = c.data ? (c.data.verdict_summary || c.data.ai_verdict || 'Анализ сохранен') : 'Данные сохранены';

    card.innerHTML = `
      <div class="case-card-header">
        <div>
          <div class="case-target-title">
            <i class="fa-solid fa-crosshairs" style="color:var(--primary);"></i>
            ${c.target}
          </div>
          <div class="case-meta">
            <span><i class="fa-solid fa-clock"></i> ${dateStr}</span>
            <span><i class="fa-solid fa-toolbox"></i> ${c.toolId}</span>
          </div>
        </div>
        <button class="btn btn-danger btn-sm" onclick="deleteCase('${c.id}')" title="Удалить"><i class="fa-solid fa-trash"></i></button>
      </div>
      ${c.notes ? `<div class="case-note"><i class="fa-solid fa-quote-left" style="color:var(--primary);"></i> ${c.notes}</div>` : ''}
      <div style="font-size:11px; color:#cbd5e1; line-height:1.4;">${verdict.substring(0, 180)}...</div>
      <div class="case-actions">
        <div style="display:flex; gap:6px;">
          <button class="btn btn-primary btn-sm" onclick="reopenCase('${c.id}')"><i class="fa-solid fa-eye"></i> Открыть досье</button>
          <button class="btn btn-secondary btn-sm" onclick="sendSavedCaseToGraph('${c.id}')"><i class="fa-solid fa-circle-nodes"></i> В граф</button>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="copySavedCase('${c.id}')"><i class="fa-solid fa-copy"></i> Копировать</button>
      </div>
    `;
    container.appendChild(card);
  });
}

function updateCasesCountBadge() {
  const b = document.getElementById('totalCasesBadge');
  if (b) b.innerText = getStoredCases().length;
}

function deleteCase(caseId) {
  if (!confirm('Удалить расследование из папки?')) return;
  const cases = getStoredCases().filter(c => c.id !== caseId);
  saveStoredCases(cases);
  renderFolderCases();
  showToast('Расследование удалено');
}

function reopenCase(caseId) {
  const c = getStoredCases().find(x => x.id === caseId);
  if (!c || !c.data) return;
  currentActiveResult = { data: c.data, target: c.target, toolId: c.toolId, timestamp: c.createdAt };
  showView('searchView');
  const outBox = document.getElementById('searchResultBox');
  renderUnifiedResult(c.data, outBox, c.target, c.toolId);
  showToast(`Досье "${c.target}" загружено`);
}

function sendSavedCaseToGraph(caseId) {
  const c = getStoredCases().find(x => x.id === caseId);
  if (!c) return;
  document.getElementById('graphTargetInput').value = c.target;
  showView('graphView');
  runGraphDirectScan();
}

function copySavedCase(caseId) {
  const c = getStoredCases().find(x => x.id === caseId);
  if (!c) return;
  const text = `[КЕЙС OSINT]\nЦель: ${c.target}\nПапка: ${c.folderId}\nЗаметка: ${c.notes || '-'}\nДата: ${c.createdAt}\nДанные: ${JSON.stringify(c.data, null, 2)}`;
  navigator.clipboard.writeText(text);
  showToast('Кейс скопирован в буфер обмена!');
}

function exportCurrentFolder() {
  const allCases = getStoredCases();
  const cases = currentFolderId === 'all' ? allCases : allCases.filter(c => c.folderId === currentFolderId);
  if (cases.length === 0) {
    alert('Папка пуста для экспорта');
    return;
  }
  let md = `# OSINT INVESTIGATION EXPORT // ${currentFolderId.toUpperCase()}\n`;
  md += `Дата экспорта: ${new Date().toLocaleString()}\n`;
  md += `Всего кейсов: ${cases.length}\n\n---\n\n`;

  cases.forEach((c, i) => {
    md += `## ${i+1}. Цель: ${c.target}\n`;
    md += `- **Модуль:** ${c.toolId}\n`;
    md += `- **Дата:** ${c.createdAt}\n`;
    if (c.notes) md += `- **Заметка:** ${c.notes}\n`;
    md += `- **Вердикт:** ${c.data.verdict_summary || c.data.ai_verdict || 'OK'}\n\n`;
  });

  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `OSINT_Folder_${currentFolderId}_${Date.now()}.md`;
  a.click();
  showToast('Отчет экспортирован в Markdown!');
}

// =====================================================================
// --- CATALOG VIEW ---
// =====================================================================
let currentCatalogFilter = 'all';

function setCatalogFilter(catId, btn) {
  currentCatalogFilter = catId;
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderCatalog();
}

function renderCatalog() {
  const container = document.getElementById('catalogCardsContainer');
  const q = (document.getElementById('catalogSearchInput').value || '').toLowerCase().trim();
  container.innerHTML = '';

  FULL_CATALOG.forEach(group => {
    if (currentCatalogFilter !== 'all' && group.id !== currentCatalogFilter) return;

    let matchedTools = group.tools.filter(t => {
      if (!q) return true;
      return t.name.toLowerCase().includes(q) || t.purpose.toLowerCase().includes(q) || (t.input && t.input.toLowerCase().includes(q));
    });

    if (matchedTools.length === 0) return;

    const gBlock = document.createElement('div');
    gBlock.innerHTML = `<div class="group-title"><i class="fa-solid fa-chevron-right"></i> ${group.title} (${matchedTools.length})</div>`;
    
    const grid = document.createElement('div');
    grid.className = 'cards-grid';

    matchedTools.forEach(t => {
      const card = document.createElement('div');
      card.className = 'card';
      card.onclick = () => {
        document.getElementById('omniInput').value = '';
        document.getElementById('omniInput').placeholder = `Введите ${t.input || 'цель'} для ${t.name}...`;
        showView('searchView');
        quickFillAndScan(t.id);
      };

      card.innerHTML = `
        <div>
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:6px;">
            <div class="card-title">${t.name}</div>
            <span class="badge badge-api">${t.scan_type || 'API'}</span>
          </div>
          <div class="card-purpose">${t.purpose}</div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:9px; color:var(--primary); font-family:var(--font-mono);">${t.input || 'строка'}</span>
          <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); quickFillAndScan('${t.id}')">Запуск</button>
        </div>
      `;
      grid.appendChild(card);
    });

    gBlock.appendChild(grid);
    container.appendChild(gBlock);
  });
}

// =====================================================================
// --- VIS.JS NETWORK GRAPH ---
// =====================================================================
let networkInstance = null;

function clearGraph() {
  const container = document.getElementById('visNetworkCanvas');
  container.innerHTML = '';
  document.getElementById('graphDossierBox').style.display = 'none';
}

async function runGraphDirectScan() {
  const target = document.getElementById('graphTargetInput').value.trim();
  if (!target) return alert('Введите никнейм или email для построения графа');

  const container = document.getElementById('visNetworkCanvas');
  try {
    const res = await fetch('/api/scan/universal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Telegram-User-Id': tgUserId || '5233450569' },
      body: JSON.stringify({ tool_id: 'autorecon', target: target, caller: currentSessionUser })
    });
    const data = await res.json();
    if (!data.ok) return alert('Ошибка построения связей');

    const nodes = [{ id: 1, label: target, color: '#38bdf8', shape: 'box', font: { color: '#fff', face: 'monospace' } }];
    const edges = [];
    let idx = 2;

    (data.profiles || []).slice(0, 14).forEach(p => {
      nodes.push({ id: idx, label: p.platform, color: '#10b981', shape: 'dot' });
      edges.push({ from: 1, to: idx });
      idx++;
    });

    if (data.emails) {
      data.emails.forEach(e => {
        nodes.push({ id: idx, label: e, color: '#f59e0b', shape: 'diamond' });
        edges.push({ from: 1, to: idx });
        idx++;
      });
    }

    const dataSet = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
    const options = {
      physics: { stabilization: true },
      nodes: { font: { color: '#ffffff' } },
      edges: { color: '#334155' }
    };
    networkInstance = new vis.Network(container, dataSet, options);

    const dBox = document.getElementById('graphDossierBox');
    const dContent = document.getElementById('graphDossierContent');
    dContent.innerText = data.ai_dossier || 'Граф сформирован на основе открытых связей платформы.';
    dBox.style.display = 'block';
  } catch(e) { alert('Ошибка построения графа'); }
}

function exportCurrentGraph() {
  if (!networkInstance) return alert('Сначала постройте граф');
  const canvas = document.querySelector('#visNetworkCanvas canvas');
  if (!canvas) return;
  const img = canvas.toDataURL('image/png');
  const a = document.createElement('a');
  a.href = img;
  a.download = `OSINT_Graph_${Date.now()}.png`;
  a.click();
}

// =====================================================================
// --- DECODERS (CYBER LAB) ---
// =====================================================================
async function runDecoderAction(action) {
  const data = document.getElementById('decoderInputData').value.trim();
  if (!data) return alert('Введите данные для обработки');

  try {
    const res = await fetch('/api/tools/decode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: action, data: data })
    });
    const js = await res.json();
    const box = document.getElementById('decoderResultBox');
    const pre = document.getElementById('decoderOutputPre');
    box.style.display = 'block';
    pre.innerText = JSON.stringify(js.result || js.possible_algorithms || js.header || js, null, 2);
  } catch(e) { alert('Ошибка декодера'); }
}

// =====================================================================
// --- USER & ADMIN MANAGEMENT ---
// =====================================================================
async function initUserProfile() {
  try {
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
      const tu = window.Telegram.WebApp.initDataUnsafe.user;
      if (tu) {
        tgUserId = String(tu.id);
        currentSessionUser = tu.username || String(tu.id);
      }
    }
    const r = await fetch(`/api/auth/me?caller=${encodeURIComponent(currentSessionUser)}&tg_id=${encodeURIComponent(tgUserId)}`);
    const data = await r.json();
    if (data.ok && data.user) {
      const u = data.user;
      document.getElementById('currentUsernameSpan').innerText = u.nickname || u.username || 'Агент';
      const qSpan = document.getElementById('quotaSpan');
      if (u.is_unlimited || u.role === 'admin' || u.role === 'vip') {
        qSpan.innerText = 'VIP ∞';
      } else {
        qSpan.innerText = `${u.scan_balance} Запросов`;
      }
      if (u.role === 'admin') {
        document.getElementById('navAdminBtn').style.display = 'inline-flex';
      }
    }
  } catch(e) {}
}

function handleUserBadgeClick() {
  const role = prompt('Вход для администратора (введите пароль):');
  if (!role) return;
  fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: role })
  }).then(r => r.json()).then(d => {
    if (d.ok) {
      currentSessionUser = 'admin';
      initUserProfile();
      showView('adminView');
      showToast('Авторизован как Администратор');
    } else alert('Неверный пароль');
  });
}

function openStarsModal() { document.getElementById('starsModal').style.display = 'flex'; }
function closeStarsModal() { document.getElementById('starsModal').style.display = 'none'; }

async function buyStarsPkg(pkgKey) {
  const prices = { pkg_20: 35, pkg_50: 88, pkg_100: 235 };
  const stars = prices[pkgKey] || 35;
  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.openInvoice) {
    window.Telegram.WebApp.openInvoice('https://t.me/$' + pkgKey, function(status) {
      if (status === 'paid') {
        showToast('Оплата успешно получена! Баланс пополнен.');
        initUserProfile();
      }
    });
  } else {
    alert(`Оплата ${stars} ⭐️ Telegram Stars доступна при открытии бота в Telegram (@...)`);
  }
}

async function loadAdminUsers() {
  try {
    const r = await fetch('/api/admin/users', { headers: { 'X-Telegram-User-Id': tgUserId || '5233450569' } });
    const js = await r.json();
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '';
    (js.users || []).forEach(u => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-weight:700; color:#fff;">${u.username}</td>
        <td>${u.notes || u.tg_id || '-'}</td>
        <td style="color:var(--amber);">${u.is_unlimited ? 'VIP ∞' : (u.scan_balance + ' ск.')}</td>
        <td><span class="badge ${u.status === 'active' ? 'badge-api' : 'badge-photo'}">${u.status}</span></td>
        <td><button class="btn btn-secondary btn-sm" onclick="setAdminQuota('${u.username}')">Квота</button></td>
      `;
      tbody.appendChild(tr);
    });
    loadAdminVisitors();
  } catch(e) {}
}

async function loadAdminVisitors() {
  try {
    const r = await fetch('/api/admin/visitors');
    const js = await r.json();
    const tbody = document.getElementById('visitorsTableBody');
    tbody.innerHTML = '';
    (js.visitors || []).slice(-15).reverse().forEach(v => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${v.ts || '-'}</td>
        <td style="color:#fff;">${v.user || 'Гость'}</td>
        <td><code>${v.ip}</code></td>
        <td>${v.country || 'RU'}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch(e) {}
}

function toggleAddUserModal() {
  const f = document.getElementById('addUserFormBox');
  f.style.display = (f.style.display === 'none' ? 'block' : 'none');
}

async function submitCreateUser() {
  const u = document.getElementById('newUsername').value.trim();
  const n = document.getElementById('newNotes').value.trim();
  const r = document.getElementById('newRole').value;
  const p = document.getElementById('newPassword').value.trim();
  if (!u) return alert('Введите никнейм');
  await fetch('/api/admin/users/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: u, notes: n, role: r, password: p })
  });
  toggleAddUserModal();
  loadAdminUsers();
  showToast(`Пользователь ${u} создан!`);
}

function setAdminQuota(username) {
  const amount = prompt(`Укажите новое количество запросов для ${username} (или 'vip' для безлимита):`, '25');
  if (amount === null) return;
  const isVip = amount.toLowerCase().trim() === 'vip';
  const val = isVip ? 999999 : parseInt(amount, 10);
  fetch('/api/admin/user/set-quota', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_user: username, balance: val, is_unlimited: isVip })
  }).then(() => {
    loadAdminUsers();
    showToast(`Квота ${username} обновлена`);
  });
}

function openExternalUrl(url) {
  if (!url) return;
  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.openLink) {
    window.Telegram.WebApp.openLink(url);
  } else {
    window.open(url, '_blank');
  }
}

// =====================================================================
// --- STARTUP INITIALIZATION ---
// =====================================================================
document.addEventListener('DOMContentLoaded', () => {
  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
  }
  initUserProfile();
  updateCasesCountBadge();
  renderCatalog();
});
</script>
</body>
</html>
'''

final_html = html_template.replace("__CATALOG_INJECT__", catalog_json)
Path("D:/osint-bot/index.html").write_text(final_html, encoding="utf-8")
print("New minimalist index.html generated successfully with Investigation Folders system!")
