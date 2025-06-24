# hapmgr

**hapmgr** is a lightweight Qt5-based application written in Python for Debian-based systems.  
Its primary purpose is to manage (install/uninstall) individual applications included in the `hamradio-all` metapackage.

---

## Features

- Install and uninstall hamradio applications with a simple GUI
- Displays current installation status of each package
- Dynamically updates the list of available applications from the metapackage
- Multilingual interface (English, Italian, Spanish, French, German)
- Debian `.deb` package available for easy installation

---

## Installation

You can install the application using the provided `.deb` package available in the [Releases](./releases) section of this repository:

```bash
sudo apt install ./hapmgr_0.6_all.deb
```

---

## Usage

After installation, you'll find it in system menu, or launch **hapmgr** from command line by running:

```bash
sudo hapmgr
```

Use the graphical interface to:

- View all applications included in `hamradio-all`
- Install or remove individual packages
- Refresh the application list as needed

---

## Source Structure

- `hapmgr/`: Source code of the Qt5 application
- `update_app_list.py`: Script to regenerate the list of available hamradio applications from the current `hamradio-all` metapackage
- `locale/`: Translation files managed using Babel (`.po` and `.mo`)

---

## Localization

**hapmgr** uses [Babel](https://babel.pocoo.org/) for internationalization.  
Currently supported languages:

- English (`en`)
- Italian (`it`)
- Spanish (`es`)
- French (`fr`)
- German (`de`)

---

## License

This project is licensed under the **GNU Lesser General Public License (LGPL)**.  
See the [LICENSE](./LICENSE) file for details.

---

## Contributing

Feel free to submit issues or pull requests.  
Translations, bug fixes, and improvements are welcome!

---

## Author

I8ZSE
Giorgio L. Rutigliano  
giorgio[at]i8zse.eu
