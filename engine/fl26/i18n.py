"""Text the engine shows the user (plan labels, backup descriptions, errors) in English and
Brazilian Portuguese. The app sets the language with the `set_language` RPC.
Game terms (positions, abilities, skills) are not translated anywhere: they match FL26."""
from __future__ import annotations

LANG = "en"

S = {
    "en": {
        "err.notClub": "this squad is not identified as a club, so it cannot be synced",
        "err.madeUp": "eFootball has no player licence for this club (its squad is invented names), "
                      "so efootballdb cannot sync it: FL26's own squad is kept",
        "err.noLeague": "this league is not part of the career",
        "err.unknownEdit": "unknown edit {kind}",
        "err.createdNotMoved": "your own player is not moved by squad tools",
        "err.noRecord": "this player has no career record: use create instead",
        "err.max40": "a squad holds at most 40 players",
        "err.hasRecord": "{name} already has a career record",
        "err.needsEdit": "creating a player FL26 lacks needs the option file (EDIT00000000)",
        "err.spareNoRecord": "the borrowed ID {pid} for {real} has no career record",
        "err.nothing": "nothing staged",
        "err.noEditSquad": "the option file has no squad for this club",
        "err.refused": "refused: the edits would introduce problems: ",
        "err.noCareer": "no career is open",
        "err.noFolder": "that folder does not exist",
        "err.gameRunning": "the game is running: close it first",
        "err.gameRunningSave": "the game is running; it holds the save in memory and would overwrite the edits. Close it first",
        "err.notVerified": "{name} did not verify after writing; the backup was restored",
        "err.noExe": "{exe} is not in that folder",
        "err.noSpare": "no spare database player left",
        "err.noMate": "the destination squad has no usable teammate record",
        "skip.twoClubs": "{name}: listed by {a} and {b}",
        "skip.over40": "{name}: {club} would exceed 40 players",
        "lab.release": "Release {name} from {club}",
        "lab.move": "Move {name}: {src} → {dst}",
        "lab.add": "Add {name} to {club}",
        "lab.create": "Create {name} at {club}",
        "lab.newToFl26": " (new to FL26)",
        "lab.numbers": "{club}: real shirt numbers",
        "lab.captain": "{club} captain: {name}",
        "desc.more": " + {n} more",
        "desc.atClub": "{n} edits at {club}",
        "desc.acrossClubs": "{n} edits across {c} clubs",
        "desc.edits": "{n} edits",
        "desc.optionFile": "Option file: {n} players new to FL26 ({title})",
        "desc.beforeRestore": "Before restoring the backup of {when}",
        "count.move": ("move", "moves"), "count.release": ("release", "releases"),
        "count.add": ("free player added", "free players added"), "count.new": ("new player", "new players"),
        "count.attr": ("rating edit", "rating edits"), "count.created": ("edit to your player", "edits to your player"),
        "count.manager": ("manager change", "manager changes"), "count.shirt": ("shirt number", "shirt numbers"),
        "count.renumber": ("squad renumbered", "squads renumbered"), "count.captain": ("captain", "captains"),
        "count.tactics_copy": ("tactics copy", "tactics copies"),
        "count.dedupe": ("squad repaired", "squads repaired"),
    },
    "pt": {
        "err.notClub": "este elenco não foi identificado como um clube, então não pode ser sincronizado",
        "err.madeUp": "o eFootball não tem licença de jogadores deste clube (o elenco tem nomes inventados), "
                      "então o efootballdb não pode sincronizá-lo: o elenco do próprio FL26 é mantido",
        "err.noLeague": "esta liga não faz parte da carreira",
        "err.unknownEdit": "alteração desconhecida: {kind}",
        "err.createdNotMoved": "o seu jogador não é movido pelas ferramentas de elenco",
        "err.noRecord": "este jogador não tem registro na carreira: use criar",
        "err.max40": "um elenco tem no máximo 40 jogadores",
        "err.hasRecord": "{name} já tem registro na carreira",
        "err.needsEdit": "criar um jogador que o FL26 não tem precisa do arquivo de opções (EDIT00000000)",
        "err.spareNoRecord": "o ID emprestado {pid} para {real} não tem registro na carreira",
        "err.nothing": "nada na fila",
        "err.noEditSquad": "o arquivo de opções não tem elenco para este clube",
        "err.refused": "recusado: as alterações criariam problemas: ",
        "err.noCareer": "nenhuma carreira aberta",
        "err.noFolder": "essa pasta não existe",
        "err.gameRunning": "o jogo está aberto: feche-o primeiro",
        "err.gameRunningSave": "o jogo está aberto; ele guarda o save na memória e sobrescreveria as alterações. Feche-o primeiro",
        "err.notVerified": "{name} não conferiu depois de gravar; o backup foi restaurado",
        "err.noExe": "o {exe} não está nessa pasta",
        "err.noSpare": "não há mais jogadores reserva no banco de dados",
        "err.noMate": "o elenco de destino não tem um registro de colega utilizável",
        "skip.twoClubs": "{name}: listado por {a} e {b}",
        "skip.over40": "{name}: {club} passaria de 40 jogadores",
        "lab.release": "{club}: dispensar {name}",
        "lab.move": "Transferir {name}: {src} → {dst}",
        "lab.add": "{club}: contratar {name}",
        "lab.create": "{club}: criar {name}",
        "lab.newToFl26": " (novo no FL26)",
        "lab.numbers": "{club}: números reais",
        "lab.captain": "{club}: capitão {name}",
        "desc.more": " + mais {n}",
        "desc.atClub": "{n} alterações · {club}",
        "desc.acrossClubs": "{n} alterações em {c} clubes",
        "desc.edits": "{n} alterações",
        "desc.optionFile": "Arquivo de opções: {n} jogadores novos no FL26 ({title})",
        "desc.beforeRestore": "Antes de restaurar o backup de {when}",
        "count.move": ("transferência", "transferências"), "count.release": ("dispensa", "dispensas"),
        "count.add": ("jogador livre contratado", "jogadores livres contratados"),
        "count.new": ("jogador novo", "jogadores novos"),
        "count.attr": ("alteração de atributo", "alterações de atributos"),
        "count.created": ("alteração no seu jogador", "alterações no seu jogador"),
        "count.manager": ("troca de técnico", "trocas de técnico"),
        "count.shirt": ("número de camisa", "números de camisa"),
        "count.renumber": ("elenco renumerado", "elencos renumerados"), "count.captain": ("capitão", "capitães"),
        "count.tactics_copy": ("cópia de táticas", "cópias de táticas"),
        "count.dedupe": ("elenco reparado", "elencos reparados"),
    },
}


def set_lang(lang):
    global LANG
    LANG = lang if lang in S else "en"
    return LANG


def tr(key, **kw):
    s = S[LANG].get(key, S["en"][key])
    return s.format(**kw)


def count(op_kind, n):
    """'3 moves' / '1 transferência' for a backup summary."""
    key = {"manager_swap": "count.manager", "manager_set": "count.manager"}.get(op_kind, f"count.{op_kind}")
    one, many = S[LANG].get(key) or S["en"].get(key) or (op_kind, op_kind)
    return f"{n} {one if n == 1 else many}"
