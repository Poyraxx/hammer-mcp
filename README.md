# hammer mcp

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
