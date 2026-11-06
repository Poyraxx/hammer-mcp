# Hammer mcp

[English](#english) | [Türkçe](#türkçe)

## English

**Hammer** is Valve's map editor for Source engine games such as Garry's Mod. It is used to build rooms, walls and floors, place models and lights, add player spawn points, and set up map interactions. [Hammer++](https://ficool2.github.io/HammerPlusPlus-Website/) is a modified version of Hammer with bug fixes and editing improvements.

Control Hammer++ from Codex, Claude, or the terminal. Includes 16 MCP tools for map files, brushes, entities, materials, menus, dialogs, and compilation.

Requires 64-bit Windows, Python 3.10+, and Hammer++ Garry's Mod build 8873.

Installation:

```powershell
git clone https://github.com/Poyraxx/hammer-mcp.git
cd hammer-mcp
python -m pip install -r requirements.txt
```

Default Hammer++ path: `C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\bin\win64\hammerplusplus.exe`. If installed elsewhere, set `HAMMER_EXE` to the full executable path.

Usage:

```powershell
python .\server.py list
python .\server.py hammer_status '{}'
python .\server.py hammer_commands '{"query":"View"}'
```

For MCP setup, replace the `server.py` path in the [Codex example](codex.example.toml) or [Claude example](mcp.example.json) with your own path. Add the Codex entry to `.codex/config.toml`. Save the Claude Code example as `.mcp.json`, or merge its `mcpServers` entry into Claude Desktop's `claude_desktop_config.json`. Reconnect your client afterward.

Running `server.py` without arguments starts the MCP server.

Save editor changes with `hammer_save` before editing a VMF file. File edits require its current `sha256` and create a backup. Use `hammer_reload` to load file changes into the editor. `hammer_compile` runs VBSP, VVIS, and VRAD.

Use `/` in asset paths. New property values cannot contain double quotes, line breaks, or backslashes.

## Türkçe

**Hammer**, Garry's Mod gibi Source motorunu kullanan oyunlar için harita hazırlamaya yarayan Valve editörüdür. Oda, duvar ve zemin oluşturmak; model, ışık ve oyuncu başlangıç noktaları yerleştirmek; harita içindeki etkileşimleri ayarlamak için kullanılır. [Hammer++](https://ficool2.github.io/HammerPlusPlus-Website/), hata düzeltmeleri ve düzenleme iyileştirmeleri içeren bir Hammer sürümüdür.

Hammer++'ı Codex, Claude veya terminalden kontrol et. Harita dosyaları, brush, entity, malzeme, menü, diyalog ve derleme işlemleri için 16 MCP aracı içerir.

Windows 64 bit, Python 3.10+ ve Hammer++ Garry's Mod build 8873 gerektirir.

Kurulum:

```powershell
git clone https://github.com/Poyraxx/hammer-mcp.git
cd hammer-mcp
python -m pip install -r requirements.txt
```

Varsayılan Hammer++ yolu: `C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\bin\win64\hammerplusplus.exe`. Farklı bir konuma kuruluysa `HAMMER_EXE` değişkenini exe dosyasının tam yoluna ayarla.

Kullanım:

```powershell
python .\server.py list
python .\server.py hammer_status '{}'
python .\server.py hammer_commands '{"query":"View"}'
```

MCP kurulumu için [Codex örneğindeki](codex.example.toml) veya [Claude örneğindeki](mcp.example.json) `server.py` yolunu kendi dosya yolunla değiştir. Codex kaydını `.codex/config.toml` dosyasına ekle. Claude Code örneğini `.mcp.json` olarak kaydet veya `mcpServers` kaydını Claude Desktop'ın `claude_desktop_config.json` dosyasıyla birleştir. Ardından istemciyi yeniden bağla.

Argümansız `server.py`, MCP sunucusunu başlatır.

VMF dosyasını düzenlemeden önce editördeki değişiklikleri `hammer_save` ile kaydet. Dosya değişiklikleri güncel `sha256` gerektirir ve yedek oluşturur. Değişiklikleri editöre yüklemek için `hammer_reload` kullan. `hammer_compile`, VBSP, VVIS ve VRAD'ı çalıştırır.

Dosya yollarında `/` kullan. Yeni özellik değerleri çift tırnak, satır sonu veya ters eğik çizgi içeremez.
