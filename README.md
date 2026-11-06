# hammer mcp

[English](#english) | [Türkçe](#türkçe)

## English

A local MCP and terminal interface for Hammer++ Garry's Mod build 8873. Requires 64-bit Windows, Python 3.10 or later, and an installed copy of Hammer++. REA is not a runtime dependency.

16 tools; 176 menu commands read from DLL resources; open documents, file operations, dialog fields, checkboxes, lists, and tabs. Entity creation/deletion, keyvalue changes, movement, and rotation use Hammer's `Worldcraft_ShellMessageWnd` / `WM_COPYDATA` interface. No mouse input, keyboard events, screenshots, DLL injection, or executable patches are used.

The VMF tools create brushes/entities, edit objects by id, move and duplicate them, and apply materials. Full VMF reading/writing also provides access to camera, displacement, I/O, instance, visgroup, and Hammer++ block data. There is no separate live API for every specialized editor tool. After changing geometry on disk, use `hammer_reload`.

Installation:

```powershell
git clone https://github.com/Poyraxx/hammer-mcp.git
cd hammer-mcp
python -m pip install -r requirements.txt
```

The default Hammer++ location is `C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\bin\win64\hammerplusplus.exe`. For a different location, set the `HAMMER_EXE` environment variable to the full executable path. Hammer++ must be installed in Garry's Mod's `bin\win64` directory.

From the project directory:

```powershell
python .\server.py list
python .\server.py hammer_status '{}'
python .\server.py hammer_commands '{"query":"View"}'
```

Running `server.py` without arguments starts the stdio MCP server. In the [Codex example](codex.example.toml) and [Claude example](mcp.example.json), replace `C:/tools/hammer-mcp/server.py` with the full path to your downloaded file. If your MCP client uses a different Python installation, set `command` to the full path of the Python executable where you installed the dependencies.

Add the Codex configuration to `.codex/config.toml` in your project root. For Claude Code, save the JSON example as `.mcp.json` in your project root. For Claude Desktop, merge the same `mcpServers` entry into your existing `claude_desktop_config.json`. Keep other MCP entries and reconnect the client to load the new tools. Downloading this repository does not automatically change client settings.

Before reading a map file, save editor changes with `hammer_save`. File edits require the latest `sha256`; the previous contents are copied to `.hammer-mcp-backups` and verified. Native entity selection uses classname and origin; use a VMF id when multiple entities of the same class share an origin. Native batches can partially complete; check `completed` and `failed`. `modified: null` does not mean there are no unsaved changes. Save prompts are not dismissed automatically.

VMF values retain their serialized representation. New values do not support double quotes, line breaks, or backslashes; use `/` in model/material paths. A backslash handling issue was observed during real map reloads in this build and compared with Valve's [TokenReader source](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/tier1/tokenreader.cpp). Full VMF writing preserves the supplied raw representation; it does not validate every semantic rule of advanced formats.

```powershell
python -m unittest discover -s .\tests -p test_*.py -v
python .\tests\check_live.py
```

The second command opens and compiles a separate test map in a real Hammer++ instance. Results are written to `logs/live-check.json`; compiler output is stored in `logs/`. Raw analysis dumps, test maps, and Hammer++/Garry's Mod files are not included in this repository.

Build 8873 was verified with 13 automated tests, a real MCP connection, live entity operations, file opening/saving, and VBSP/VVIS/VRAD compilation. Garry's Mod gameplay and every specialized Hammer++ tool have not been tested.

## Türkçe

Hammer++ Garry's Mod build 8873 için yerel MCP ve terminal bağlantısı. Windows 64 bit, Python 3.10 veya üzeri ve kurulu Hammer++ gerektirir. REA çalışma zamanı bağımlılığı değildir.

16 araç; DLL kaynaklarından okunan 176 menü komutu; açık belgeler, dosya işlemleri, diyalog alanları, onay kutuları, listeler ve sekmeler. Entity ekleme/silme, özellik değiştirme, taşıma ve döndürme işlemleri Hammer'ın `Worldcraft_ShellMessageWnd` / `WM_COPYDATA` arayüzüne gider. Fare, klavye olayı, ekran görüntüsü, DLL enjeksiyonu veya program yaması kullanılmaz.

VMF araçları brush/entity oluşturur, nesneleri id ile değiştirir, taşır, çoğaltır ve malzeme uygular. Tam VMF okuma/yazma ile kamera, displacement, I/O, instance, visgroup ve Hammer++ bloklarının dosya verisine de erişilir. Özel editör araçlarının her biri için ayrı bir canlı API yoktur. Geometri dosyada değiştirildiğinde `hammer_reload` gerekir.

Kurulum:

```powershell
git clone https://github.com/Poyraxx/hammer-mcp.git
cd hammer-mcp
python -m pip install -r requirements.txt
```

Varsayılan Hammer++ konumu `C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\bin\win64\hammerplusplus.exe`. Farklı bir konum için `HAMMER_EXE` ortam değişkenini tam exe yoluna ayarla. Hammer++ dosyaları Garry's Mod'un `bin\win64` klasörüne kurulmuş olmalıdır.

Proje klasöründen:

```powershell
python .\server.py list
python .\server.py hammer_status '{}'
python .\server.py hammer_commands '{"query":"View"}'
```

Argümansız `server.py`, stdio MCP sunucusunu başlatır. [Codex örneğindeki](codex.example.toml) ve [Claude örneğindeki](mcp.example.json) `C:/tools/hammer-mcp/server.py` yolunu indirdiğin dosyanın tam yoluyla değiştir. MCP istemcisinin farklı bir Python kullanması durumunda `command` alanına bağımlılıkları kurduğun Python'un tam yolunu yaz.

Codex ayarını proje kökündeki `.codex/config.toml` dosyasına ekle. Claude Code için JSON örneğini proje kökündeki `.mcp.json` dosyasına kaydet. Claude Desktop için aynı `mcpServers` kaydını mevcut `claude_desktop_config.json` içeriğiyle birleştir. Diğer MCP kayıtlarını koru ve yeni araçları görmek için istemciyi yeniden bağla. Bu istemci ayarları indirme sonrasında otomatik değiştirilmez.

Harita dosyasını okumadan önce editördeki değişiklikleri `hammer_save` ile kaydet. Dosya değişikliklerinde son `sha256` gerekir; eski içerik `.hammer-mcp-backups` klasörüne doğrulanarak kopyalanır. Native entity seçimi classname ve origin ile yapılır; aynı yerde aynı sınıftan birden fazla entity varsa VMF id kullan. Native işlem grubu kısmen tamamlanabilir; `completed` ve `failed` alanlarını kontrol et. `modified: null`, kaydedilmemiş değişiklik olmadığı anlamına gelmez. Kaydetme soruları otomatik kapatılmaz.

VMF değerleri dosyadaki gösterimleriyle korunur. Yeni değerlerde çift tırnak, satır sonu ve ters eğik çizgi desteklenmez; model/malzeme yollarında `/` kullan. Bu sürümde geri yükleme sırasında ters eğik çizgi işleme hatası gerçek dosyada gözlendi; Valve'ın [TokenReader kaynağındaki](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/tier1/tokenreader.cpp) davranışla da karşılaştırıldı. Tam VMF yazma, verilen ham dosya gösterimini korur; ileri biçimlerin bütün anlamsal kurallarını doğrulamaz.

```powershell
python -m unittest discover -s .\tests -p test_*.py -v
python .\tests\check_live.py
```

İkinci komut gerçek Hammer++ üzerinde ayrı bir test haritası açar ve derler. Sonuç `logs/live-check.json`, derleyici çıktıları `logs/` içindedir. Ham analiz dökümleri, test haritaları ve Hammer++/Garry's Mod dosyaları bu depoya dahil değildir.

Build 8873 üzerinde 13 otomatik test, gerçek MCP bağlantısı, canlı entity işlemleri, dosya açma/kaydetme ve VBSP/VVIS/VRAD derlemesi doğrulandı. Garry's Mod içinde oynanış ve bütün özel Hammer++ araçları test edilmedi.
