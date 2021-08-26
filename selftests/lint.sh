#!/bin/sh -e
echo "** Running lint..."

if [ "$AVOCADO_PARALLEL_LINT_JOBS" ]; then
    PYLINT_OPTIONS="--jobs=$AVOCADO_PARALLEL_LINT_JOBS";
fi

PYLINT=$(which pylint-3 2>/dev/null || which pylint)

# Those are files from our main packages, we should follow the .pylintrc file with all
# enabled by default. Some are disabled, we are working to reduce this list.
FILES=$(git ls-files '*.py' ':!:selftests*')
${PYLINT} ${PYLINT_OPTIONS} ${FILES}

# This is a special case, so we added those two exceptions on top of all
# disabled messages, defined at .pylintrc. Ideally we should fix those
# warnings (if possible)
FILES=$(git ls-files 'selftests*.py')
${PYLINT} ${PYLINT_OPTIONS} --disable=W0212,W0703 ${FILES}

# This is just a Python 3 porting check. We are not still ready for a full
# --py3k, so we are enabling just a few checks at this time.
#
# We are not using pylintrc here because this is a completely different type of check.
# Maybe soon, we can have multiple pytlintrc files.
FILES=$(git ls-files '*.py')
${PYLINT} ${PYLINT_OPTIONS} \
	--disable=W0212,W0511,W0703,W0707,R,C,E1101,E1120,E0401,I0011 \
	--enable=W1601,W1602,W1603,W1604,W1605,W1606,W1607,W1608,W1609,W1610,W1611,W1612,W1613,W1614,W1615,W1616,W1617,W1620,W1621,W1622,W1623,W1624,W1625,W1626,W1627,W1628,W1629,W1630,W1634,W1635,W1636,W1637,W1638,W1639,W1640,W1642,W1643,W1644,W1645,W1646,W1647,W1648,W1649,W1650,W1651,W1652,W1653,W1654,W1655,W1656,W1657,W1658,W1659,W1660,W1661,W1662 \
	${FILES}
