# This absoulutely needs a cache, else we can't stop recursing until we know all owners for all products...
#
# Since we know that the non-owned products will not get renowned by the user by other means,
# we can just check for ownership on the products that have an ADD_PRODUCT transaction for the user.
# between now and the cached time.
#
# However, the opposite way is more difficult. The cache will store which products are owned by which users,
# but we still need to check if the user passes out of ownership for the item, without needing to check past
# the cache time. Maybe we also need to store the queue number(s) per user/product combo in the cache? What if
# a user has products multiple places in the queue, interleaved with other users?
