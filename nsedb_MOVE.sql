WITH mrows AS (
    DELETE FROM fno
    WHERE
        "SYMBOL" = 'BANKNIFTY'
    RETURNING *
)
INSERT INTO fno_banknifty
SELECT * FROM mrows;

