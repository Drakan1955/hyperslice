# Hyperslice - (c) 2026 Costantino Vita ("Drakan"). SPDX-License-Identifier: GPL-3.0-or-later; see LICENSE.txt.
# Geometry ported from "Sculpture Generator 1" by Carlo H. Sequin (UC Berkeley),
# released under the GPL with his permission (e-mails of 2 and 18 November 2026). Not supported or endorsed by him.
"""Traduzione italiana dell'interfaccia (attiva solo se Blender e' in italiano)."""

_IT = {
    "Scherk tower": "Torre di Scherk",
    "3-branch tower": "Torre a 3 rami",
    "Twisted tower": "Torre ritorta",
    "180° arch": "Arco 180°",
    "Toroidal closure": "Chiusura toroidale",
    "Double closure": "Doppia chiusura",
    "3-branch closure": "Chiusura a 3 rami",
    "Classic sculptures": "Sculture classiche",
    "Séquin's demos": "Demo di Séquin",
    "More sculptures": "Altre sculture",
    "Add from preset": "Aggiungi da preset",
    "Séquin's demo {n}": "Demo {n} di Séquin",
    "{b} branches, {s} storeys, bend {w}°, twist {t}°": "{b} rami, {s} piani, curvatura {w}°, torsione {t}°",
    "Live update": "Aggiornamento in tempo reale",
    "Recompute the sculpture while you move the sliders": "Ricalcola la scultura mentre muovi i cursori",
    "Animation": "Animazione",
    "Recompute the sculpture at every frame, so that animated sliders (keyframes or drivers) change its shape. Uses the full detail when rendering": "Ricalcola la scultura a ogni fotogramma, così i cursori animati (chiavi o driver) ne cambiano la forma. Nel render usa il dettaglio pieno",
    "Limit live detail": "Limita il dettaglio in tempo reale",
    "If the mesh would be too heavy, temporarily lowers the detail; 'Regenerate' always uses the full value":
        "Se la mesh sarebbe troppo pesante, riduce temporaneamente il dettaglio; 'Rigenera' usa sempre il valore pieno",
    "Saddle branches": "Rami di sella",
    "Number of saddle branches (2 = classic Scherk, 3 = monkey saddle)":
        "Numero di rami della sella (2 = Scherk classica, 3 = sella a scimmia)",
    "Storeys (holes)": "Piani (fori)",
    "Grid detail": "Dettaglio griglia",
    "Storey height": "Altezza piano",
    "Flange width": "Larghezza ala",
    "As in the original, values below 0.7 are raised to 0.7": "Come nell'originale, valori sotto 0.7 vengono portati a 0.7",
    "Thickness": "Spessore",
    "0 = thin (open) surface": "0 = superficie sottile (aperta)",
    "Rim bulge": "Rigonfiamento bordo",
    "0 flat, up to 0.1 sharp edges, up to 1 triangular, above 1 elliptical":
        "0 piatto, fino a 0.1 spigoli vivi, fino a 1 triangolare, oltre 1 ellittico",
    "Total twist": "Torsione totale",
    "Total axial twist in degrees, spread over the storeys": "Torsione assiale totale in gradi, distribuita sui piani",
    "Arc bend": "Curvatura ad arco",
    "Degrees of bending (360 = closed ring, 720 = double closure)":
        "Gradi di piegatura (360 = anello chiuso, 720 = doppia chiusura)",
    "Rotation about the axis": "Rotazione attorno all'asse",
    "Scale": "Scala",
    "Detail along the axis": "Dettaglio lungo l'asse",
    "Points along the length of the sculpture; 0 = same as grid detail. Raise it for smoother rings":
        "Punti lungo la lunghezza della scultura; 0 = uguale al dettaglio griglia. Alzalo per anelli più lisci",
    "Taper": "Rastremazione",
    "Stretch angle": "Angolo dello stretch",
    "Rotates the axes of Stretch X and Y about the sculpture's axis. Hyperslice extension, saved at the end of the parameter file": "Ruota gli assi di Stretch X e Y attorno all'asse della scultura. Estensione di Hyperslice, salvata in fondo al file dei parametri",
    "Flange width at the top relative to the bottom: 1 = double, -0.5 = half. Not compatible with closed rings":
        "Larghezza dell'ala in alto rispetto al basso: 1 = il doppio, -0.5 = la metà. Non è compatibile con gli anelli chiusi",
    "Vase swell": "Rigonfiamento a vaso",
    "Widens (positive) or narrows (negative) the flange at mid-height, like a vase; ends unchanged":
        "Allarga (positivo) o stringe (negativo) l'ala a metà altezza, come un vaso; estremità invariate",
    "Reflective": "Riflettente",
    "Shiny, mirror-like surface (the environment map of Sculpture Generator 1)": "Superficie lucida, a specchio (la mappa dell'ambiente di Sculpture Generator 1)",
    "Side A": "Lato A", "Side B": "Lato B", "Rim": "Bordo", "Top lid": "Tappo alto", "Bottom lid": "Tappo basso",
    "Choose a preset": "Scegli un preset",
    "Edit Mode: parameters off": "Edit Mode: parametri inattivi",
    "Import .sg1": "Importa .sg1",
    "Save .sg1": "Salva .sg1",
    "Go back to Object Mode.": "Tornare in Object Mode.",
    "UV map": "Mappa UV",
    "Tiles": "Ripetizioni",
    "UV tiles": "Ripetizioni UV",
    "Creates a UV map: along the sculpture (U) and around it (V), one 0-1 space for each of the five materials": "Crea una mappa UV: lungo la scultura (U) e attorno a essa (V), uno spazio 0-1 per ciascuno dei cinque materiali",
    "Repeats the texture this many times (texture_tiles of the parameter file)": "Ripete la texture questo numero di volte (texture_tiles del file di parametri)",
    'Export STL (for 3D printing)': 'Esporta STL (per la stampa 3D)',
    'Exports the active mesh as a binary STL, scaled so that its largest dimension is the chosen size in millimetres (STL files have no units: slicers read the numbers as mm)': 'Esporta la mesh attiva in STL binario, in scala in modo che la dimensione massima sia quella scelta in millimetri (i file STL non hanno unità: gli slicer leggono i numeri come mm)',
    'Largest dimension (mm)': 'Dimensione massima (mm)',
    'Size of the printed sculpture. 0 = no scaling (1 Blender unit = 1 mm)': 'Dimensione della scultura stampata. 0 = nessuna scala (1 unità di Blender = 1 mm)',
    'This Blender version has no STL exporter': "Questa versione di Blender non ha l'esportatore STL",
    'Exported {name}': 'Esportato {name}',
    ': largest dimension {mm} mm': ': dimensione massima {mm} mm',
    'Save as my preset': 'Salva come mio preset',
    "Saves the current sculpture (parameters and colours) with a small picture in the list 'My presets'. A preset with the same name is replaced": "Salva la scultura attuale (parametri e colori) con una piccola immagine nell'elenco 'I miei preset'. Un preset con lo stesso nome viene sostituito",
    'My presets': 'I miei preset',
    'No saved presets yet: use "Save as my preset" in the panel.': 'Nessun preset salvato: usare "Salva come mio preset" nel pannello.',
    'Type a name for the preset': 'Scrivere un nome per il preset',
    'Preset saved, but the picture could not be made: {e}': "Preset salvato, ma non è stato possibile creare l'immagine: {e}",
    'Saved preset {name}': 'Preset {name} salvato',
    'Applies this saved preset': 'Applica questo preset salvato',
    'Apply my preset': 'Applica il mio preset',
    'Delete this preset': 'Elimina questo preset',
    'Deletes this saved preset (the parameter file and its picture)': 'Elimina questo preset salvato (il file dei parametri e la sua immagine)',
    'Preset {name} deleted': 'Preset {name} eliminato',
    "Name": "Nome",
    "Preset": "Preset",
    "Adds a Scherk/Collins sculpture": "Aggiunge una scultura di Scherk/Collins",
    "Regenerate (full detail)": "Rigenera (dettaglio pieno)",
    "Apply preset": "Applica preset",
    "Apply": "Applica",
    "Freeze (plain mesh)": "Congela (mesh normale)",
    "Regenerates at full detail and turns the mesh into an ordinary editable / exportable mesh":
        "Rigenera a dettaglio pieno e rende la mesh una normale mesh modificabile / esportabile",
    "Sculpture frozen: it is now a plain mesh": "Scultura congelata: ora è una mesh normale",
    "Check watertightness (for 3D printing)": "Controlla tenuta (per stampa 3D)",
    "Counts open or non-manifold edges of the mesh": "Conta gli spigoli aperti o non manifold della mesh",
    "{n} open edges (mesh is not watertight)": "{n} spigoli non chiusi (mesh non a tenuta)",
    "Mesh is closed and manifold: ready for STL export": "Mesh chiusa e manifold: pronta per l'esportazione STL",
    "Import parameters": "Importa parametri",
    "Reads a Sculpture Generator parameter file (.sg1 or .txt). If a sculpture is selected it modifies it, otherwise it creates a new one":
        "Legge un file di parametri del Sculpture Generator (.sg1 o .txt). Se hai una scultura selezionata la modifica, altrimenti ne crea una nuova",
    "not a Sculpture Generator parameter file (first line '{header}' missing)":
        "non è un file di parametri dello Sculpture Generator (manca la prima riga '{header}')",
    "Read {name}": "Letto {name}",
    "({n} texture/background/view lines ignored)": "({n} righe su texture/sfondo/vista ignorate)",
    "values brought within limits:": "valori portati nei limiti:",
    "Save parameters": "Salva parametri",
    "Writes the parameters in the Sculpture Generator format. If you give no extension, .sg1 is added (for the original program type it yourself in the name, e.g. .txt or .sg1)":
        "Scrive i parametri nel formato del Sculpture Generator. Se non scrivi l'estensione viene aggiunta .sg1 (per il programma originale scrivila tu nel nome, es. .txt o .sg1)",
    "Saved {name}, but detail along the axis, taper and swell do not exist in the format and are not saved":
        "Salvato {name}, ma dettaglio lungo l'asse, rastremazione e rigonfiamento non esistono nel formato e non sono salvati",
    "Saved {name}": "Salvato {name}",
    "Random variant": "Variante casuale",
    "Proposes new parameters (New) or small variations of the current ones (Tweak). Discards combinations that do not close by itself. Undo with Ctrl+Z":
        "Propone parametri nuovi (Nuova) o piccole variazioni di quelli attuali (Ritocco). Scarta da sola le combinazioni che non chiudono. Annulla con Ctrl+Z",
    "Type": "Tipo", "New": "Nuova", "Completely new parameters": "Parametri del tutto nuovi",
    "Tweak": "Ritocco", "Small variations of the current values": "Piccole variazioni dei valori attuali",
    "Seed": "Seme",
    "0 = random; the same seed repeats the same variant": "0 = a caso; lo stesso seme ripete la stessa variante",
    "No valid variant found: I left the previous values": "Nessuna variante valida trovata: ho lasciato i valori di prima",
    "Select a sculpture to edit it.": "Seleziona una scultura per modificarla.",
    "The ends do not match.": "Le estremità non combaciano.",
    "Twist that closes: {a:g} or {b:g}": "Torsione che chiude: {a:g} o {b:g}",
    "Taper and closed ring:": "Rastremazione e anello chiuso:",
    "the ends cannot match": "le estremità non possono combaciare",
    "Colors": "Colori",
    "Preview at detail {d}: press Regenerate": "Anteprima a dettaglio {d}: premi Rigenera",
    "Perforated": "Traforato",
    "Turns the surface into an irregular, Voronoi-like lattice, with modifiers (turn it off to get the solid sculpture back). The UV map is lost": "Trasforma la superficie in un reticolo irregolare, tipo Voronoi, con dei modificatori (disattivarlo per riavere la scultura piena). La mappa UV va persa",
    "Cells": "Celle",
    "Approximate number of cells of the lattice": "Numero indicativo di celle del reticolo",
    "Wire thickness": "Spessore fili",
    "Thickness of the lattice wires": "Spessore dei fili del reticolo",
    "UV map: lost with Perforated": "Mappa UV: persa con Traforato",
    "Many cells: slow and heavy": "Molte celle: lento e pesante",
    "Turn on Perforated last": "Attivare Traforato per ultimo",
    "Faces: {n}": "Facce: {n}",
}

from . import presets_extra as _pe
for _k, _g, _n, _en, _tr, _p in _pe.EXTRA:
    _IT.setdefault(_en, _tr[0])

TRANSLATIONS = {"it_IT": {}}
for _en, _it in _IT.items():
    for _ctx in ("*", "Operator"):
        TRANSLATIONS["it_IT"][(_ctx, _en)] = _it

# francese, tedesco, spagnolo
from . import translations_extra as _x
for _i, _codes in _x.LOCALES.items():
    for _code in _codes:
        TRANSLATIONS[_code] = {}
        for _en, _tr in _x._X.items():
            for _ctx in ("*", "Operator"):
                TRANSLATIONS[_code][(_ctx, _en)] = _tr[_i]
