# Scraper Improvements - Implementation Summary

## Overview
Three major improvements have been implemented in the scraper system:

1. **Dynamic Image Wait Times**: Wait based on actual image count instead of fixed delays
2. **Real-Time Data Insertion**: Save events to database as they're scraped (not after all are done)
3. **Image Folder Filtering**: Prevent cross-contamination by filtering images to specific verba folders

---

## 1. Dynamic Image Wait Times

### Location
File: `/home/user/better-e-leiloes/backend/scraper.py`
Function: `_extract_gallery()` (lines 355-386)

### How It Works

1. **Detects Image Counter**: Looks for `.custom-galleria-footer`, `.p-galleria-footer`, or `.better-image-badge`
2. **Parses Count**: Extracts total images from formats like:
   - `"1/7"` → 7 images
   - `"📷 7"` → 7 images
3. **Calculates Wait Time**: `(total_images × 2.5) + 1` seconds
   - Example: 7 images = (7 × 2.5) + 1 = **18.5 seconds**
4. **Waits Dynamically**: Allows all images to load before scraping

### Code Example
```python
# Parse "X/Y" ou "📷 Y" para obter total de imagens
match = re.search(r'(\d+)/(\d+)|📷\s*(\d+)', footer_text)
if match:
    total_images = int(match.group(2) if match.group(2) else match.group(3))
    print(f"🖼️ Total de imagens detectadas: {total_images}")

    # Calcula tempo de espera: 2.5s por imagem + 1s buffer
    wait_time = (total_images * 2.5) + 1
    print(f"⏳ Aguardando {wait_time:.1f}s para todas as imagens carregarem...")
    await asyncio.sleep(wait_time)
```

### Fallback Strategy
- If counter not found: waits 2 seconds (default)
- If parsing fails: waits 3 seconds (safe fallback)
- Ensures scraper always continues even if detection fails

---

## 2. Real-Time Data Insertion (Stage 2)

### Location
- **Backend**: `/home/user/better-e-leiloes/backend/main.py` (lines 448-486)
- **Scraper**: `/home/user/better-e-leiloes/backend/scraper.py` (lines 1174-1179)

### How It Works

**Before**: All events scraped first, then saved to database in bulk
**After**: Each event saved immediately after being scraped

### Flow

1. **Stage 2 Endpoint** creates callback function:
```python
async def save_event_callback(event: EventData):
    """Salva evento na BD em tempo real"""
    async with get_db() as db:
        await db.save_event(event)
        await cache_manager.set(event.reference, event)
        print(f"  💾 {event.reference} guardado em tempo real")
```

2. **Passes callback** to scraper:
```python
callback = save_event_callback if save_to_db else None
events = await scraper.scrape_details_by_ids(references, on_event_scraped=callback)
```

3. **Scraper calls callback** immediately after scraping each event:
```python
for idx, result in enumerate(results):
    if isinstance(result, EventData):
        events.append(result)
        print(f"  ✓ {batch[idx]}")

        # 🔥 INSERÇÃO EM TEMPO REAL via callback
        if on_event_scraped:
            try:
                await on_event_scraped(result)
            except Exception as e:
                print(f"  ⚠️ Erro ao salvar {batch[idx]}: {e}")
```

### Benefits
- **Progressive saves**: Data available in database immediately
- **Fault tolerance**: If scraper crashes mid-run, already-scraped events are saved
- **Real-time monitoring**: See data appear in database as scraping progresses
- **No memory buildup**: Events saved and released immediately

---

## 3. Image Folder Filtering (Stage 3)

### Location
File: `/home/user/better-e-leiloes/backend/scraper.py`
Function: `_scrape_images_only()` (lines 1338-1427)

### The Problem
Previously, the image scraper was capturing images from **multiple verba folders**, causing cross-contamination:

**Example Bug**: Event `LO1418222025` (verba_121561) was getting:
- ✅ 13 images from `verba_121561` (correct)
- ❌ 13 images from `verba_115332`, `verba_117298`, `verba_121229` (incorrect)
- **Total**: 26 images instead of 13

### How It Works Now

1. **Network Request Interception**: Uses Playwright's `page.route()` to intercept API calls to `Verbas_Fotos/verba_X/`
2. **Folder Detection**: Extracts folder name from the FIRST intercepted image URL
3. **Filtering**: Only accepts subsequent images from that specific folder
4. **Rejection**: Ignores images from different folders

### Code Example
```python
async def _scrape_images_only(self, reference: str) -> List[str]:
    intercepted_images = []
    verba_folder = None  # 🔥 Track the correct folder

    async def handle_route(route):
        nonlocal verba_folder
        img_url = route.request.url

        if 'Verbas_Fotos/verba_' in img_url:
            # Extract folder name (e.g., "verba_121561")
            match = re.search(r'(verba_\d+)', img_url)
            if match:
                folder = match.group(1)

                # 🎯 First image sets the folder
                if verba_folder is None:
                    verba_folder = folder
                    print(f"🎯 Folder detectado: {verba_folder}")

                # ✅ Only accept images from the correct folder
                if folder == verba_folder:
                    intercepted_images.append(img_url)
                    print(f"📸 {len(intercepted_images)}: {img_url.split('/')[-1]}")
                else:
                    # ❌ Ignore images from other folders
                    print(f"⏭️ Ignorado (folder diferente): {folder}")

        await route.continue_()

    await page.route("**/*", handle_route)
    # ... rest of implementation
```

### Console Output Example
```
🎯 Folder detectado: verba_121561
📸 1: 28102025171229_800.jpg
📸 2: 28102025171230_800.jpg
📸 3: 28102025171231_800.jpg
⏭️ Ignorado (folder diferente): verba_115332
⏭️ Ignorado (folder diferente): verba_117298
📸 4: 28102025171232_800.jpg
...
✅ 13 imagens de verba_121561
```

### Benefits
- **No Cross-Contamination**: Each event only gets its own images
- **Accurate Data**: Image count matches actual event images
- **Debugging**: Clear console output shows what's being accepted/rejected
- **Reliable**: Uses first intercepted image as source of truth

---

## Testing Instructions

### Prerequisites
1. Playwright browsers installed: `playwright install chromium`
2. Backend server running: `cd backend && python main.py`

### Test 1: Dynamic Image Wait Times

Run Stage 3 (images) on a single event and watch console output:

```bash
curl -X POST "http://localhost:8000/api/scrape/stage3/images" \
  -H "Content-Type: application/json" \
  -d '{"references": ["LO-2024-001"]}'
```

**Expected Output**:
```
📊 Contador de imagens: 1/7
🖼️ Total de imagens detectadas: 7
⏳ Aguardando 18.5s para todas as imagens carregarem...
```

### Test 2: Real-Time Data Insertion

Run Stage 2 with multiple events and monitor database:

```bash
curl -X POST "http://localhost:8000/api/scrape/stage2/details?save_to_db=true" \
  -H "Content-Type: application/json" \
  -d '{"references": ["LO-2024-001", "LO-2024-002", "LO-2024-003"]}'
```

**Expected Output**:
```
📋 Stage 2: Scraping detalhes de 3 eventos...
  ✓ LO-2024-001
  💾 LO-2024-001 guardado em tempo real
  ✓ LO-2024-002
  💾 LO-2024-002 guardado em tempo real
  ✓ LO-2024-003
  💾 LO-2024-003 guardado em tempo real
✅ Stage 2 completo: 3 eventos / 0 falhas
```

Note: Events appear in database **immediately** after scraping (not at the end).

### Test 3: Image Folder Filtering

Run the verification test script:

```bash
cd backend && python test_image_folder_filter.py
```

**Expected Output**:
```
🧪 Testing Folder Extraction from URLs
✅ PASS | Expected: verba_121561 | Got: verba_121561
✅ PASS | Expected: verba_115332 | Got: verba_115332
...

🧪 Testing Folder Filtering Logic
🎯 Folder detectado: verba_121561
✅ ACEITE  | verba_121561 | image_001.jpg
✅ ACEITE  | verba_121561 | image_002.jpg
❌ REJEITADO | verba_115332 | image_003.jpg
...
✅ Filtro funcionando corretamente!

🧪 Testing Real-World Scenario
Event: LO1418222025 (verba_121561)
Imagens ANTES do fix: 26 (13 corretas + 13 erradas)
Imagens DEPOIS do fix: 13
✅ BUG CORRIGIDO!

✅ ALL TESTS PASSED - Image folder filtering is working correctly!
```

**Real Scraper Test**: Run Stage 3 on an event and verify console output shows folder filtering:

```bash
curl -X POST "http://localhost:8000/api/scrape/stage3/images" \
  -H "Content-Type: application/json" \
  -d '{"references": ["LO1418222025"]}'
```

Watch console for:
- `🎯 Folder detectado: verba_XXXXX` (first image sets folder)
- `📸 1: filename.jpg` (accepted images)
- `⏭️ Ignorado (folder diferente): verba_YYYYY` (rejected from wrong folders)
- `✅ N imagens de verba_XXXXX` (final count from correct folder only)

---

## Stage Workflow (Updated)

### Stage 1: Get IDs Only
```
POST /api/scrape/stage1/ids?max_pages=1
```
- Scrapes listing pages
- Returns only event references (IDs)
- Fast, lightweight

### Stage 2: Scrape Details (Real-Time Insertion)
```
POST /api/scrape/stage2/details?save_to_db=true
```
- Takes list of references from Stage 1
- Scrapes full event details (NO images)
- **Saves each event immediately to database**
- Returns all scraped events

### Stage 3: Scrape Images (Dynamic Wait)
```
POST /api/scrape/stage3/images
```
- Takes list of references
- **Detects image count and waits dynamically**
- Scrapes all images with proper timing
- Updates events with image URLs

---

## Summary of Changes

✅ **Dynamic Image Wait Times**:
- Lines 1390-1413 in `scraper.py`
- Detects image count from gallery footer
- Calculates: `(count × 2.5) + 1` seconds
- Ensures all images load before scraping

✅ **Real-Time Data Insertion**:
- Lines 367-434 in `main.py` (Stage 1 endpoint)
- Lines 448-486 in `main.py` (Stage 2 endpoint)
- Lines 1174-1179 in `scraper.py` (callback execution)
- Events saved immediately after scraping
- Progressive database population

✅ **Image Folder Filtering**:
- Lines 1338-1427 in `scraper.py` (`_scrape_images_only()`)
- Extracts folder from first image URL
- Filters to only accept images from correct verba folder
- Prevents cross-contamination between events
- Tested with `test_image_folder_filter.py`

---

## Bug Fixes

### Critical: Image Cross-Contamination (Fixed)
**Issue**: Events were getting images from multiple verba folders
- Event `LO1418222025` (verba_121561) was receiving 26 images:
  - 13 correct from verba_121561
  - 13 incorrect from verba_115332, verba_117298, verba_121229, etc.

**Solution**: Implement folder filtering in request interception
- Track folder from first intercepted image
- Only accept subsequent images from that folder
- Ignore images from different folders

**Result**: Each event now gets only its own images
- Event `LO1418222025` now correctly gets **13 images** (all from verba_121561)
- No cross-contamination
- Accurate image counts

---

## Notes

- All features are **backward compatible**
- Real-time insertion can be disabled with `save_to_db=false`
- Dynamic wait has safe fallbacks if detection fails
- Image filtering is always active in Stage 3
- No breaking changes to existing API
