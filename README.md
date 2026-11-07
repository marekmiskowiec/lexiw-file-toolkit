# lexiw-file-toolkit

Mój „kombajn” do pracy na plikach: zmiana formatów, kompresja zdjęć i masowa zmiana nazw.
Powstał z dawnego skryptu `heicToWebp`, który zmniejszał zdjęcia z iPhone'a (HEIC) przed wrzuceniem na Facebooka.

## Instalacja

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Użycie

Domyślnie zdjęcia są brane z folderu `input/`, a wyniki trafiają do `output/` (oba foldery są w `.gitignore`).

### compress: lżejsze zdjęcia do wrzucenia na Facebooka

```bash
python toolkit.py compress                 # input/ -> output/, WebP, dłuższy bok max 2048 px, jakość 80
python toolkit.py compress -f jpeg         # to samo, ale JPEG
python toolkit.py compress --max-size 1600 -q 70
```

### convert: zmiana formatu (bez zmniejszania)

```bash
python toolkit.py convert input -o output -f webp    # formaty: webp, jpeg/jpg, png
python toolkit.py convert zdjecie.HEIC -f jpeg --scale 0.5
```

Czyta HEIC/HEIF, JPEG, PNG, WebP, BMP i TIFF. Obrót zdjęcia jest zachowany, a metadane EXIF
(w tym lokalizacja GPS z telefonu) nie są kopiowane do plików wynikowych.

### rename: zmiana nazw według wzoru

```bash
python toolkit.py rename output -p "hot-wheels-{n:03d}"           # podgląd: hot-wheels-001.webp, ...
python toolkit.py rename output -p "hot-wheels-{n:03d}" --apply   # naprawdę zmienia nazwy
python toolkit.py rename output -p "{name}-fb" --ext webp --apply
```

`{n}` to licznik (`--start` ustawia pierwszą wartość), `{name}` to stara nazwa. Bez `--apply` skrypt tylko pokazuje, co zrobi.

Szczegóły każdej komendy: `python toolkit.py <komenda> --help`.
