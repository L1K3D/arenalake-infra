const fs = require('fs').promises
const getTheme = require('./libs/theme')

const midnightTheme = getTheme({
  theme: 'midnight',
  name: 'Dracula Midnight',
})

// Write themes

fs.mkdir('./themes', { recursive: true })
  .then(() =>
    Promise.all([
      fs.writeFile(
        './themes/dracula-midnight.json',
        JSON.stringify(midnightTheme, null, 2)
      ),
    ])
  )
  .catch(() => process.exit(1))
