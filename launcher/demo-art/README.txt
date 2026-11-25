K.OS private demo art
=====================

Put official logo pictures here to show them on the launcher tiles during
investor and partner demos. Everything in this folder except this README is
ignored by Git, so the logos never reach the public GitHub repo or the K.OS image.

Download each logo only from the company's own brand or press page and use it
as provided (no redrawing, no recoloring). Before retail, either remove these
files or get written permission from each company.

File names (use exactly these, lowercase):

  netflix.png     Netflix tile
  hbomax.png      HBO Max tile
  xcloud.png      Xbox Bulut Oyun tile
  browser.png     Internet tile
  windows.png     Windows'a Gec tile

You can also use .jpg, .webp or .svg instead of .png.
Game tiles work the same way, named by game id (for example kuzey-isigi.png).

Picture tips:
  - Square picture, at least 512 x 512 pixels.
  - Logo in the middle with plenty of empty space around it, on a solid
    background color. The same picture is used on the square Home tiles and
    on the wider Apps tiles, so the top and bottom get trimmed on wide tiles.

To check it worked: open the launcher again. The tile shows your picture
instead of the K.OS design. To go back, delete the file.

Private demo setup (demo.js)
----------------------------
demo.js in this folder replaces the sample games with real ones and sets the
order of the Home row for demos. It is ignored by Git like everything here.
Delete it to go back to the public sample setup.

Background artwork
------------------
On the Home screen, each game's official Steam artwork is loaded by its
steamAppId (set in demo.js) and blended into the background. For demos without
internet, save that artwork here as <game id>-hero.jpg (for example
rdr2-hero.jpg). Wide pictures work best (Steam's are 1920 x 620).
