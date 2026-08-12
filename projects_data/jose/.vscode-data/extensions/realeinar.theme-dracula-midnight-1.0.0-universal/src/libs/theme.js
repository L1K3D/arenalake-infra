const chroma = require('chroma-js')
const { getColors } = require('./colors')

// Choosing colors
// There are two ways to define what color is used:

// 1. Color scale from dracula.
//    e.g. "textLink.foreground": themes({ light: color.red, dark: color.blue, dimmed: color.green }),
// 2. Hex value: All themes will use this scale. Only use for exceptions
//    e.g. "textLink.foreground": "#fff",

function getTheme({ theme, name }) {
  // Usage: color.background
  const color = getColors(theme)

  return {
    name: name,
    colors: {
      focusBorder: chroma(color.purple).alpha(0.6).hex(),
      foreground: color.comment,
      descriptionForeground: color.foreground,
      errorForeground: color.red,
      'widget.shadow': color.shadow,
      'icon.foreground': color.foreground,
      'selection.background': chroma(color.purple).alpha(0.5).hex(),
      'sash.hoverBorder': color.pink,

      'button.background': color.selection,
      'button.foreground': color.foreground,

      'button.secondaryBackground': color.red,
      'button.secondaryForeground': color.foreground,
      'button.secondaryHoverBackground': color.ansi9,

      'checkbox.background': color.backgroundLight,
      'checkbox.foreground': color.foreground,
      'checkbox.border': color.backgroundDarker,

      'dropdown.background': color.background,
      'dropdown.border': color.backgroundDarker,
      'dropdown.foreground': color.foreground,
      'dropdown.listBackground': color.background,

      'input.background': color.backgroundLight,
      'input.border': color.backgroundDarker,
      'input.foreground': color.foreground,
      'input.placeholderForeground': chroma(color.foreground).alpha(0.5).hex(),

      'inputOption.activeBorder': color.purple,

      'inputValidation.infoBorder': color.pink,
      'inputValidation.warningBorder': color.orange,
      'inputValidation.errorBorder': color.red,

      'badge.background': color.selection,
      'badge.foreground': color.foreground,

      'progressBar.background': color.pink,

      'titleBar.activeForeground': color.foreground,
      'titleBar.activeBackground': color.backgroundDark,
      'titleBar.inactiveForeground': color.comment,
      'titleBar.inactiveBackground': color.backgroundDark,
      'titleBar.border': color.backgroundDarker,

      'activityBar.foreground': color.foreground,
      'activityBar.inactiveForeground': color.comment,
      'activityBar.background': color.backgroundDark,
      'activityBarBadge.foreground': color.foreground,
      'activityBarBadge.background': color.pink,
      'activityBar.activeBorder': color.pink,
      'activityBar.border': color.backgroundDarker,

      'sideBar.foreground': color.foreground,
      'sideBar.background': color.backgroundDark,
      'sideBar.border': color.backgroundDarker,
      'sideBarTitle.foreground': color.foreground,
      'sideBarSectionHeader.background': color.backgroundDark,
      'sideBarSectionHeader.foreground': color.foreground,
      'sideBarSectionHeader.border': color.backgroundDarker,

      'list.hoverForeground': color.comment,
      'list.inactiveSelectionForeground': color.cyan,
      'list.activeSelectionForeground': color.cyan,
      'list.hoverBackground': color.backgroundLight,
      'list.inactiveSelectionBackground': color.backgroundLight,
      'list.activeSelectionBackground': color.backgroundLight,
      'list.focusForeground': color.comment,
      'list.focusBackground': color.backgroundLight,
      'list.highlightForeground': color.cyan,
      'list.dropBackground': color.selection,
      'list.warningForeground': color.orange,
      'list.errorForeground': color.red,

      'tree.indentGuidesStroke': color.backgroundLighter,
      'tree.tableColumnsBorder': color.backgroundDarker,

      'notificationCenterHeader.foreground': color.foreground,
      'notificationCenterHeader.background': color.background,
      'notificationCenter.border': color.backgroundDarker,
      'notifications.foreground': color.foreground,
      'notifications.background': color.backgroundLight,
      'notifications.border': color.backgroundDark,
      'notificationToast.border': color.backgroundDarker,
      'notificationLink.foreground': color.cyan,
      'notificationsErrorIcon.foreground': color.red,
      'notificationsWarningIcon.foreground': color.orange,
      'notificationsInfoIcon.foreground': color.cyan,

      'pickerGroup.border': color.purple,
      'pickerGroup.foreground': color.cyan,

      'statusBar.foreground': color.comment,
      'statusBar.background': color.backgroundDark,
      'statusBar.border': color.backgroundDarker,
      'statusBar.noFolderForeground': chroma(color.purple).alpha(0.6).hex(),
      'statusBar.noFolderBackground': color.background,
      'statusBar.debuggingBackground': color.red,
      'statusBar.debuggingForeground': color.backgroundDarker,
      'statusBarItem.activeBackground': color.backgroundLight,
      'statusBarItem.hoverBackground': color.background,
      'statusBarItem.prominentForeground': color.foreground,
      'statusBarItem.prominentBackground': color.red,
      'statusBarItem.prominentHoverBackground': color.ansi9,
      'statusBarItem.remoteForeground': color.backgroundDarker,
      'statusBarItem.remoteBackground': color.comment,

      'editorGroup.border': color.backgroundDarker,
      'editorGroup.dropBackground': color.backgroundLight,
      'editorGroupHeader.tabsBackground': color.backgroundDark,
      'editorGroupHeader.tabsBorder': color.backgroundDarker,

      'tab.activeForeground': color.foreground,
      'tab.inactiveForeground': color.comment,
      'tab.inactiveBackground': color.backgroundDark,
      'tab.activeBackground': color.backgroundDark,
      'tab.border': color.backgroundDarker,
      'tab.activeBorder': color.background,
      'tab.unfocusedActiveBorder': color.background,
      'tab.activeBorderTop': color.pink,
      'tab.activeModifiedBorder': color.yellow,

      'breadcrumb.foreground': color.comment,
      'breadcrumb.focusForeground': color.backgroundDark,
      'breadcrumb.activeSelectionForeground': color.backgroundDark,
      'breadcrumb.background': color.backgroundDark,
      'breadcrumbPicker.background': color.backgroundDarker,

      'editorWidget.background': color.background,
      'editorWidget.border': color.purple,
      'editorLineNumber.foreground': color.comment,
      'editorLineNumber.activeForeground': color.white,
      'editorIndentGuide.background': color.nonText,
      'editorIndentGuide.activeBackground': chroma(color.white)
        .alpha(0.15)
        .hex(),
      'editorWhitespace.foreground': color.nonText,
      'editorCursor.foreground': color.cyan,
      'editorLink.activeForeground': color.cyan,
      'editorCodeLens.foreground': color.comment,
      'editorLightBulb.foreground': color.yellow,
      'editorLightBulbAutoFix.foreground': color.cyan,
      'editorError.foreground': color.red,
      'editorWarning.foreground': color.cyan,
      'editorMarkerNavigation.background': color.backgroundDark,

      'editor.background': color.backgroundDark,
      'editor.foreground': color.foreground,
      'editor.foldBackground': color.backgroundDark,
      'editor.findMatchBackground': chroma(color.pink).alpha(0.5).hex(),
      'editor.findMatchHighlightBackground': chroma(color.purple)
        .alpha(0.1)
        .hex(),
      'editor.selectionBackground': color.selection,
      'editor.selectionHighlightBackground': color.backgroundLighter,
      'editor.wordHighlightBackground': chroma(color.cyan).alpha(0.2).hex(),
      'editor.wordHighlightStrongBackground': chroma(color.green)
        .alpha(0.2)
        .hex(),
      'editor.findRangeHighlightBackground': color.lineHighlight,
      'editor.hoverHighlightBackground': chroma(color.cyan).alpha(0.2).hex(),
      'editor.lineHighlightBorder': color.selection,
      'editor.rangeHighlightBackground': chroma(color.purple).alpha(0.15).hex(),
      'editor.snippetTabstopHighlightBackground': color.background,
      'editor.snippetTabstopHighlightBorder': color.comment,
      'editor.snippetFinalTabstopHighlightBackground': color.background,
      'editor.snippetFinalTabstopHighlightBorder': color.green,
      'editorBracketMatch.border': color.transparent,
      'editorBracketMatch.background': color.selection,

      'editorSuggestWidget.background': color.backgroundDark,
      'editorSuggestWidget.border': color.backgroundDarker,
      'editorSuggestWidget.foreground': color.foreground,
      'editorSuggestWidget.selectedBackground': color.selection,

      'editorHoverWidget.background': color.background,
      'editorHoverWidget.border': color.comment,

      'editorGutter.modifiedBackground': color.cyan,
      'editorGutter.addedBackground': color.green,
      'editorGutter.deletedBackground': color.red,

      'editorRuler.foreground': color.nonText,

      'diffEditor.insertedTextBackground': chroma(color.green)
        .alpha(0.125)
        .hex(),
      'diffEditor.removedTextBackground': chroma(color.red).alpha(0.3).hex(),
      'diffEditor.diagonalFill': color.backgroundLighter,

      'scrollbar.shadow': color.transparent,
      'scrollbarSlider.background': chroma(color.purple).alpha(0.3).hex(),
      'scrollbarSlider.hoverBackground': chroma(color.purple).alpha(0.4).hex(),
      'scrollbarSlider.activeBackground': chroma(color.purple).alpha(0.5).hex(),

      'editorOverviewRuler.border': color.transparent,
      'editorOverviewRuler.selectionHighlightForeground': color.orange,
      'editorOverviewRuler.wordHighlightForeground': color.cyan,
      'editorOverviewRuler.wordHighlightStrongForeground': color.green,
      'editorOverviewRuler.modifiedForeground': chroma(color.cyan)
        .alpha(0.8)
        .hex(),
      'editorOverviewRuler.addedForeground': chroma(color.green)
        .alpha(0.8)
        .hex(),
      'editorOverviewRuler.deletedForeground': chroma(color.red)
        .alpha(0.8)
        .hex(),
      'editorOverviewRuler.errorForeground': chroma(color.red).alpha(0.8).hex(),
      'editorOverviewRuler.warningForeground': chroma(color.orange)
        .alpha(0.8)
        .hex(),
      'editorOverviewRuler.infoForeground': chroma(color.cyan).alpha(0.8).hex(),
      'editorOverviewRuler.currentContentForeground': color.green,
      'editorOverviewRuler.incomingContentForeground': color.purple,

      'editorBracketHighlight.foreground1': color.foreground,
      'editorBracketHighlight.foreground2': color.pink,
      'editorBracketHighlight.foreground3': color.cyan,
      'editorBracketHighlight.foreground4': color.green,
      'editorBracketHighlight.foreground5': color.purple,
      'editorBracketHighlight.foreground6': color.orange,
      'editorBracketHighlight.unexpectedBracket.foreground': color.red,

      'panel.background': color.backgroundDark,
      'panel.border': color.backgroundDarker,
      'panelTitle.activeBorder': color.purple,
      'panelTitle.activeForeground': color.foreground,
      'panelTitle.inactiveForeground': color.comment,

      'terminal.foreground': color.foreground,
      'terminal.background': color.backgroundDark,
      'terminal.ansiBlack': color.ansi0,
      'terminal.ansiRed': color.ansi1,
      'terminal.ansiGreen': color.ansi2,
      'terminal.ansiYellow': color.ansi3,
      'terminal.ansiBlue': color.ansi4,
      'terminal.ansiMagenta': color.ansi5,
      'terminal.ansiCyan': color.ansi6,
      'terminal.ansiWhite': color.ansi7,
      'terminal.ansiBrightBlack': color.ansi8,
      'terminal.ansiBrightRed': color.ansi9,
      'terminal.ansiBrightGreen': color.ansi10,
      'terminal.ansiBrightYellow': color.ansi11,
      'terminal.ansiBrightBlue': color.ansi12,
      'terminal.ansiBrightMagenta': color.ansi13,
      'terminal.ansiBrightCyan': color.ansi14,
      'terminal.ansiBrightWhite': color.ansi15,

      'gitDecoration.addedResourceForeground': color.yellow,
      'gitDecoration.modifiedResourceForeground': color.cyan,
      'gitDecoration.deletedResourceForeground': color.red,
      'gitDecoration.untrackedResourceForeground': color.green,
      'gitDecoration.ignoredResourceForeground': chroma(color.purple)
        .alpha(0.4)
        .hex(),
      'gitDecoration.conflictingResourceForeground': color.orange,
      'gitDecoration.submoduleResourceForeground': color.pink,

      'merge.currentHeaderBackground': chroma(color.green).alpha(0.9).hex(),
      'merge.incomingHeaderBackground': chroma(color.purple).alpha(0.9).hex(),

      'debugToolBar.background': color.backgroundDark,

      'peekView.border': color.backgroundDarker,
      'peekViewEditor.matchHighlightBackground': chroma(color.pink)
        .alpha(0.4)
        .hex(),
      'peekViewResult.matchHighlightBackground': chroma(color.pink)
        .alpha(0.4)
        .hex(),
      'peekViewEditor.background': color.backgroundDark,
      'peekViewResult.background': color.backgroundDark,
      'peekViewResult.fileForeground': color.foreground,
      'peekViewResult.lineForeground': color.foreground,
      'peekViewResult.selectionBackground': color.selection,
      'peekViewResult.selectionForeground': color.foreground,
      'peekViewTitle.background': color.backgroundDark,
      'peekViewTitleDescription.foreground': color.comment,
      'peekViewTitleLabel.foreground': color.foreground,

      'settings.headerForeground': color.foreground,
      'settings.modifiedItemIndicator': color.orange,
      'settings.dropdownForeground': color.foreground,
      'settings.checkboxForeground': color.foreground,
      'settings.textInputForeground': color.foreground,
      'settings.numberInputForeground': color.foreground,
      'settings.dropdownBackground': color.backgroundDark,
      'settings.checkboxBackground': color.backgroundDark,
      'settings.textInputBackground': color.backgroundDark,
      'settings.numberInputBackground': color.backgroundDark,
      'settings.dropdownBorder': color.backgroundDarker,
      'settings.checkboxBorder': color.backgroundDarker,
      'settings.textInputBorder': color.backgroundDarker,
      'settings.numberInputBorder': color.backgroundDarker,

      'charts.foreground': color.foreground,
      'charts.lines': color.foreground,
      'charts.red': color.red,
      'charts.blue': color.cyan,
      'charts.yellow': color.yellow,
      'charts.orange': color.orange,
      'charts.green': color.green,
      'charts.purple': color.purple,

      'banner.background': color.backgroundDarker,
      'banner.foreground': color.foreground,
      'banner.iconForeground': color.red,

      'extensionButton.prominentForeground': color.foreground,
      'extensionButton.prominentBackground': chroma(color.purple)
        .alpha(0.8)
        .hex(),
      'extensionButton.prominentHoverBackground': color.purple,

      'toolbar.hoverBackground': color.backgroundLight,

      'walkThrough.embeddedEditorBackground': color.backgroundDark,

      'listFilterWidget.background': color.backgroundLight,
      'listFilterWidget.outline': color.backgroundLighter,
      'listFilterWidget.noMatchesOutline': color.red,
    },
    semanticClass: 'theme.dracula',
    semanticHighlighting: true,
    tokenColors: [
      {
        scope: ['emphasis'],
        settings: {
          fontStyle: 'italic',
        },
      },
      {
        scope: ['strong'],
        settings: {
          fontStyle: 'bold',
        },
      },
      {
        scope: ['header'],
        settings: {
          foreground: color.purple,
        },
      },
      {
        scope: ['source'],
        settings: {
          foreground: color.foreground,
        },
      },
      {
        scope: ['meta.diff', 'meta.diff.header'],
        settings: {
          foreground: color.comment,
        },
      },
      {
        scope: ['markup.inserted'],
        settings: {
          foreground: color.green,
        },
      },
      {
        scope: ['markup.deleted'],
        settings: {
          foreground: color.red,
        },
      },
      {
        scope: ['markup.changed'],
        settings: {
          foreground: color.orange,
        },
      },
      {
        scope: ['invalid'],
        settings: {
          foreground: color.red,
          fontStyle: 'underline italic',
        },
      },
      {
        scope: ['invalid.deprecated'],
        settings: {
          foreground: color.foreground,
          fontStyle: 'underline italic',
        },
      },
      {
        scope: ['entity.name.filename'],
        settings: {
          foreground: color.yellow,
        },
      },
      {
        scope: ['markup.error'],
        settings: {
          foreground: color.red,
        },
      },
      {
        name: 'Underlined markup',
        scope: ['markup.underline'],
        settings: {
          fontStyle: 'underline',
        },
      },
      {
        name: 'Bold markup',
        scope: ['markup.bold'],
        settings: {
          fontStyle: 'bold',
          foreground: color.orange,
        },
      },
      {
        name: 'Markup headings',
        scope: ['markup.heading'],
        settings: {
          fontStyle: 'bold',
          foreground: color.purple,
        },
      },
      {
        name: 'Markup italic',
        scope: ['markup.italic'],
        settings: {
          foreground: color.yellow,
          fontStyle: 'italic',
        },
      },
      {
        name: 'Bullets, lists (prose)',
        scope: [
          'beginning.punctuation.definition.list.markdown',
          'beginning.punctuation.definition.quote.markdown',
          'punctuation.definition.link.restructuredtext',
        ],
        settings: {
          foreground: color.cyan,
        },
      },
      {
        name: 'Inline code (prose)',
        scope: ['markup.inline.raw', 'markup.raw.restructuredtext'],
        settings: {
          foreground: color.green,
        },
      },
      {
        name: 'Links (prose)',
        scope: ['markup.underline.link', 'markup.underline.link.image'],
        settings: {
          foreground: color.cyan,
        },
      },
      {
        name: 'Link text, image alt text (prose)',
        scope: [
          'meta.link.reference.def.restructuredtext',
          'punctuation.definition.directive.restructuredtext',
          'string.other.link.description',
          'string.other.link.title',
        ],
        settings: {
          foreground: color.pink,
        },
      },
      {
        name: 'Blockquotes (prose)',
        scope: ['entity.name.directive.restructuredtext', 'markup.quote'],
        settings: {
          foreground: color.yellow,
          fontStyle: 'italic',
        },
      },
      {
        name: 'Horizontal rule (prose)',
        scope: ['meta.separator.markdown'],
        settings: {
          foreground: color.comment,
        },
      },
      {
        name: 'Code blocks',
        scope: [
          'fenced_code.block.language',
          'markup.raw.inner.restructuredtext',
          'markup.fenced_code.block.markdown punctuation.definition.markdown',
        ],
        settings: {
          foreground: color.green,
        },
      },
      {
        name: 'Prose constants',
        scope: ['punctuation.definition.constant.restructuredtext'],
        settings: {
          foreground: color.purple,
        },
      },
      {
        name: 'Braces in markdown headings',
        scope: [
          'markup.heading.markdown punctuation.definition.string.begin',
          'markup.heading.markdown punctuation.definition.string.end',
        ],
        settings: {
          foreground: color.purple,
        },
      },
      {
        name: 'Braces in markdown paragraphs',
        scope: [
          'meta.paragraph.markdown punctuation.definition.string.begin',
          'meta.paragraph.markdown punctuation.definition.string.end',
        ],
        settings: {
          foreground: color.foreground,
        },
      },
      {
        name: 'Braces in markdown blockquotes',
        scope: [
          'markup.quote.markdown meta.paragraph.markdown punctuation.definition.string.begin',
          'markup.quote.markdown meta.paragraph.markdown punctuation.definition.string.end',
        ],
        settings: {
          foreground: color.yellow,
        },
      },
      {
        name: 'User-defined class names',
        scope: ['entity.name.type.class', 'entity.name.class'],
        settings: {
          foreground: color.cyan,
          fontStyle: 'normal',
        },
      },
      {
        name: 'this, super, self, etc.',
        scope: [
          'keyword.expressions-and-types.swift',
          'keyword.other.this',
          'variable.language',
          'variable.language punctuation.definition.variable.php',
          'variable.other.readwrite.instance.ruby',
          'variable.parameter.function.language.special',
        ],
        settings: {
          foreground: color.purple,
          fontStyle: 'italic',
        },
      },
      {
        name: 'Inherited classes',
        scope: ['entity.other.inherited-class'],
        settings: {
          fontStyle: 'italic',
          foreground: color.cyan,
        },
      },
      {
        name: 'Comments',
        scope: [
          'comment',
          'punctuation.definition.comment',
          'unused.comment',
          'wildcard.comment',
        ],
        settings: {
          foreground: color.comment,
        },
      },
      {
        name: 'JSDoc-style keywords',
        scope: [
          'comment keyword.codetag.notation',
          'comment.block.documentation keyword',
          'comment.block.documentation storage.type.class',
        ],
        settings: {
          foreground: color.pink,
        },
      },
      {
        name: 'JSDoc-style types',
        scope: ['comment.block.documentation entity.name.type'],
        settings: {
          foreground: color.cyan,
          fontStyle: 'italic',
        },
      },
      {
        name: 'JSDoc-style type brackets',
        scope: [
          'comment.block.documentation entity.name.type punctuation.definition.bracket',
        ],
        settings: {
          foreground: color.cyan,
        },
      },
      {
        name: 'JSDoc-style comment parameters',
        scope: ['comment.block.documentation variable'],
        settings: {
          foreground: color.orange,
          fontStyle: 'italic',
        },
      },
      {
        name: 'Constants',
        scope: ['constant', 'variable.other.constant'],
        settings: {
          foreground: color.purple,
        },
      },
      {
        name: 'Constant escape sequences',
        scope: [
          'constant.character.escape',
          'constant.character.string.escape',
          'constant.regexp',
        ],
        settings: {
          foreground: color.pink,
        },
      },
      {
        name: 'HTML tags',
        scope: ['entity.name.tag'],
        settings: {
          foreground: color.pink,
        },
      },
      {
        name: "CSS attribute parent selectors ('&')",
        scope: ['entity.other.attribute-name.parent-selector'],
        settings: {
          foreground: color.pink,
        },
      },
      {
        name: 'HTML/CSS attribute names',
        scope: ['entity.other.attribute-name'],
        settings: {
          foreground: color.green,
          fontStyle: 'italic',
        },
      },
      {
        name: 'Function names',
        scope: [
          'entity.name.function',
          'meta.function-call.object',
          'meta.function-call.php',
          'meta.function-call.static',
          'meta.method-call.java meta.method',
          'meta.method.groovy',
          'support.function.any-method.lua',
          'keyword.operator.function.infix',
        ],
        settings: {
          foreground: color.green,
        },
      },
      {
        name: 'Function parameters',
        scope: [
          'entity.name.variable.parameter',
          'meta.at-rule.function variable',
          'meta.at-rule.mixin variable',
          'meta.function.arguments variable.other.php',
          'meta.selectionset.graphql meta.arguments.graphql variable.arguments.graphql',
          'variable.parameter',
        ],
        settings: {
          fontStyle: 'italic',
          foreground: color.orange,
        },
      },
      {
        name: 'Decorators',
        scope: [
          'meta.decorator variable.other.readwrite',
          'meta.decorator variable.other.property',
        ],
        settings: {
          foreground: color.green,
          fontStyle: 'italic',
        },
      },
      {
        name: 'Decorator Objects',
        scope: ['meta.decorator variable.other.object'],
        settings: {
          foreground: color.green,
        },
      },
      {
        name: 'Keywords',
        scope: ['keyword', 'punctuation.definition.keyword'],
        settings: {
          foreground: color.pink,
        },
      },
      {
        name: 'Keyword "new"',
        scope: ['keyword.control.new', 'keyword.operator.new'],
        settings: {
          fontStyle: 'bold',
        },
      },
      {
        name: 'Generic selectors (CSS/SCSS/Less/Stylus)',
        scope: ['meta.selector'],
        settings: {
          foreground: color.pink,
        },
      },
      {
        name: 'Language Built-ins',
        scope: ['support'],
        settings: {
          fontStyle: 'italic',
          foreground: color.cyan,
        },
      },
      {
        name: 'Built-in magic functions and constants',
        scope: [
          'support.function.magic',
          'support.variable',
          'variable.other.predefined',
        ],
        settings: {
          fontStyle: 'regular',
          foreground: color.purple,
        },
      },
      {
        name: 'Built-in functions / properties',
        scope: ['support.function', 'support.type.property-name'],
        settings: {
          fontStyle: 'regular',
        },
      },
      {
        name: 'Separators (key/value, namespace, inheritance, pointer, hash, slice, etc)',
        scope: [
          'constant.other.symbol.hashkey punctuation.definition.constant.ruby',
          'entity.other.attribute-name.placeholder punctuation',
          'entity.other.attribute-name.pseudo-class punctuation',
          'entity.other.attribute-name.pseudo-element punctuation',
          'meta.group.double.toml',
          'meta.group.toml',
          'meta.object-binding-pattern-variable punctuation.destructuring',
          'punctuation.colon.graphql',
          'punctuation.definition.block.scalar.folded.yaml',
          'punctuation.definition.block.scalar.literal.yaml',
          'punctuation.definition.block.sequence.item.yaml',
          'punctuation.definition.entity.other.inherited-class',
          'punctuation.function.swift',
          'punctuation.separator.dictionary.key-value',
          'punctuation.separator.hash',
          'punctuation.separator.inheritance',
          'punctuation.separator.key-value',
          'punctuation.separator.key-value.mapping.yaml',
          'punctuation.separator.namespace',
          'punctuation.separator.pointer-access',
          'punctuation.separator.slice',
          'string.unquoted.heredoc punctuation.definition.string',
          'support.other.chomping-indicator.yaml',
          'punctuation.separator.annotation',
        ],
        settings: {
          foreground: color.pink,
        },
      },
      {
        name: 'Brackets, braces, parens, etc.',
        scope: [
          'keyword.operator.other.powershell',
          'keyword.other.statement-separator.powershell',
          'meta.brace.round',
          'meta.function-call punctuation',
          'punctuation.definition.arguments.begin',
          'punctuation.definition.arguments.end',
          'punctuation.definition.entity.begin',
          'punctuation.definition.entity.end',
          'punctuation.definition.tag.cs',
          'punctuation.definition.type.begin',
          'punctuation.definition.type.end',
          'punctuation.section.scope.begin',
          'punctuation.section.scope.end',
          'storage.type.generic.java',
          'string.template meta.brace',
          'string.template punctuation.accessor',
        ],
        settings: {
          foreground: color.foreground,
        },
      },
      {
        name: 'Variable interpolation operators',
        scope: [
          'meta.string-contents.quoted.double punctuation.definition.variable',
          'punctuation.definition.interpolation.begin',
          'punctuation.definition.interpolation.end',
          'punctuation.definition.template-expression.begin',
          'punctuation.definition.template-expression.end',
          'punctuation.section.embedded.begin',
          'punctuation.section.embedded.coffee',
          'punctuation.section.embedded.end',
          'punctuation.section.embedded.end source.php',
          'punctuation.section.embedded.end source.ruby',
          'punctuation.definition.variable.makefile',
        ],
        settings: {
          foreground: color.pink,
        },
      },
      {
        name: 'Keys (serializable languages)',
        scope: [
          'entity.name.function.target.makefile',
          'entity.name.section.toml',
          'entity.name.tag.yaml',
          'variable.other.key.toml',
        ],
        settings: {
          foreground: color.cyan,
        },
      },
      {
        name: 'Dates / timestamps (serializable languages)',
        scope: ['constant.other.date', 'constant.other.timestamp'],
        settings: {
          foreground: color.orange,
        },
      },
      {
        name: 'YAML aliases',
        scope: ['variable.other.alias.yaml'],
        settings: {
          fontStyle: 'italic underline',
          foreground: color.green,
        },
      },
      {
        name: 'Storage',
        scope: [
          'storage',
          'meta.implementation storage.type.objc',
          'meta.interface-or-protocol storage.type.objc',
          'source.groovy storage.type.def',
        ],
        settings: {
          fontStyle: 'regular',
          foreground: color.pink,
        },
      },
      {
        name: 'Types',
        scope: [
          'entity.name.type',
          'keyword.primitive-datatypes.swift',
          'keyword.type.cs',
          'meta.protocol-list.objc',
          'meta.return-type.objc',
          'source.go storage.type',
          'source.groovy storage.type',
          'source.java storage.type',
          'source.powershell entity.other.attribute-name',
          'storage.class.std.rust',
          'storage.type.attribute.swift',
          'storage.type.c',
          'storage.type.core.rust',
          'storage.type.cs',
          'storage.type.groovy',
          'storage.type.objc',
          'storage.type.php',
          'storage.type.haskell',
          'storage.type.ocaml',
        ],
        settings: {
          fontStyle: 'italic',
          foreground: color.cyan,
        },
      },
      {
        name: 'Generics, templates, and mapped type declarations',
        scope: [
          'entity.name.type.type-parameter',
          'meta.indexer.mappedtype.declaration entity.name.type',
          'meta.type.parameters entity.name.type',
        ],
        settings: {
          foreground: color.orange,
        },
      },
      {
        name: 'Modifiers',
        scope: ['storage.modifier'],
        settings: {
          foreground: color.pink,
        },
      },
      {
        name: 'RegExp string',
        scope: [
          'string.regexp',
          'constant.other.character-class.set.regexp',
          'constant.character.escape.backslash.regexp',
        ],
        settings: {
          foreground: color.yellow,
        },
      },
      {
        name: 'Non-capture operators',
        scope: ['punctuation.definition.group.capture.regexp'],
        settings: {
          foreground: color.pink,
        },
      },
      {
        name: 'RegExp start and end characters',
        scope: [
          'string.regexp punctuation.definition.string.begin',
          'string.regexp punctuation.definition.string.end',
        ],
        settings: {
          foreground: color.red,
        },
      },
      {
        name: 'Character group',
        scope: ['punctuation.definition.character-class.regexp'],
        settings: {
          foreground: color.cyan,
        },
      },
      {
        name: 'Capture groups',
        scope: ['punctuation.definition.group.regexp'],
        settings: {
          foreground: color.orange,
        },
      },
      {
        name: 'Assertion operators',
        scope: [
          'punctuation.definition.group.assertion.regexp',
          'keyword.operator.negation.regexp',
        ],
        settings: {
          foreground: color.red,
        },
      },
      {
        name: 'Positive lookaheads',
        scope: ['meta.assertion.look-ahead.regexp'],
        settings: {
          foreground: color.green,
        },
      },
      {
        name: 'Strings',
        scope: ['string'],
        settings: {
          foreground: color.yellow,
        },
      },
      {
        name: 'String quotes (temporary vscode fix)',
        scope: [
          'punctuation.definition.string.begin',
          'punctuation.definition.string.end',
        ],
        settings: {
          foreground: color.tempQuotes,
        },
      },
      {
        name: 'Property quotes (temporary vscode fix)',
        scope: [
          'punctuation.support.type.property-name.begin',
          'punctuation.support.type.property-name.end',
        ],
        settings: {
          foreground: color.tempPropertyQuotes,
        },
      },
      {
        name: 'Docstrings',
        scope: [
          'string.quoted.docstring.multi',
          'string.quoted.docstring.multi.python punctuation.definition.string.begin',
          'string.quoted.docstring.multi.python punctuation.definition.string.end',
          'string.quoted.docstring.multi.python constant.character.escape',
        ],
        settings: {
          foreground: color.comment,
        },
      },
      {
        name: 'Variables and object properties',
        scope: [
          'variable',
          'constant.other.key.perl',
          'support.variable.property',
          'variable.other.constant.js',
          'variable.other.constant.ts',
          'variable.other.constant.tsx',
        ],
        settings: {
          foreground: color.foreground,
        },
      },
      {
        name: 'Destructuring / aliasing reference name (LHS)',
        scope: [
          'meta.import variable.other.readwrite',
          'meta.object-binding-pattern-variable variable.object.property',
          'meta.variable.assignment.destructured.object.coffee variable',
        ],
        settings: {
          fontStyle: 'italic',
          foreground: color.orange,
        },
      },
      {
        name: 'Destructuring / aliasing variable name (RHS)',
        scope: [
          'meta.import variable.other.readwrite.alias',
          'meta.export variable.other.readwrite.alias',
          'meta.variable.assignment.destructured.object.coffee variable variable',
        ],
        settings: {
          fontStyle: 'normal',
          foreground: color.foreground,
        },
      },
      {
        name: 'GraphQL keys',
        scope: ['meta.selectionset.graphql variable'],
        settings: {
          foreground: color.yellow,
        },
      },
      {
        name: 'GraphQL function arguments',
        scope: ['meta.selectionset.graphql meta.arguments variable'],
        settings: {
          foreground: color.foreground,
        },
      },
      {
        name: 'GraphQL fragment name (definition)',
        scope: ['entity.name.fragment.graphql', 'variable.fragment.graphql'],
        settings: {
          foreground: color.cyan,
        },
      },
      {
        name: 'Edge cases (foreground color resets)',
        scope: [
          'constant.other.symbol.hashkey.ruby',
          'keyword.operator.dereference.java',
          'keyword.operator.navigation.groovy',
          'meta.scope.for-loop.shell punctuation.definition.string.begin',
          'meta.scope.for-loop.shell punctuation.definition.string.end',
          'meta.scope.for-loop.shell string',
          'storage.modifier.import',
          'punctuation.section.embedded.begin.tsx',
          'punctuation.section.embedded.end.tsx',
          'punctuation.section.embedded.begin.jsx',
          'punctuation.section.embedded.end.jsx',
          'punctuation.separator.list.comma.css',
          'constant.language.empty-list.haskell',
        ],
        settings: {
          foreground: color.foreground,
        },
      },
      {
        name: 'Shell variables prefixed with "$" (edge case)',
        scope: ['source.shell variable.other'],
        settings: {
          foreground: color.purple,
        },
      },
      {
        name: 'Powershell constants mistakenly scoped to `support`, rather than `constant` (edge)',
        scope: ['support.constant'],
        settings: {
          fontStyle: 'normal',
          foreground: color.purple,
        },
      },
      {
        name: 'Makefile prerequisite names',
        scope: ['meta.scope.prerequisites.makefile'],
        settings: {
          foreground: color.yellow,
        },
      },
      {
        name: 'SCSS attibute selector strings',
        scope: ['meta.attribute-selector.scss'],
        settings: {
          foreground: color.yellow,
        },
      },
      {
        name: 'SCSS attribute selector brackets',
        scope: [
          'punctuation.definition.attribute-selector.end.bracket.square.scss',
          'punctuation.definition.attribute-selector.begin.bracket.square.scss',
        ],
        settings: {
          foreground: color.foreground,
        },
      },
      {
        name: 'Haskell Pragmas',
        scope: ['meta.preprocessor.haskell'],
        settings: {
          foreground: color.comment,
        },
      },
    ],
  }
}

module.exports = getTheme
