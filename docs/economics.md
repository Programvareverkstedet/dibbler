# Dibbler economy spec v1

This document provides an overview of how dibbler counts and calculates its running event log.

It is a sort of semi-formal specification for how dibbler's economy is intended to work, and is useful for both users and developers to understand the underlying mechanics.

## Some general notes

- All calculations involving money are done in whole numbers (integers). There are no fractional krs.
- All rounding is done by rounding up to the nearest integer, in favor of the system economy - not the users.
- All rounding is done as late as possible in calculations, to avoid rounding errors accumulating.
- The system allows negative stock counts, but acts a bit weirdly and potentially unfairly when that happens.
  The system should generally warn you about this, and recommend recounting the stock whenever it happens.
- Throughout the document, the penalty multiplier and interest rate are expressed as percentages in int (e.g. `penalty_multiplier = 150` means the prices should be multiplied by `1.5`, and `interest_rate = 120` means the prices should be multiplied by `1.2`).

## Adding products - product stock and product price

This section covers what happens to the stock count and price of a product when a user adds more of that product to the system.

### Calculating the total value of products added

When a user adds a product, the resulting product price is averaged over the new products and the existing products. However, the new product price will become an integer. To avoid the economy going downwards, we round up the price after doing the averaging - i.e. in favor of the system, not the users.

### When the product count is `0` before adding.

When the product count is `0`, adding more of that product sets the product count to the amount added, and the product price will be set to the price of all products added divided by the number of products added, rounded up to the nearest integer.

```python
new_product_count: int = products_added
new_product_price: int = math.ceil(total_value_of_products_added / products_added)
```

### When the product count is greater than `0` before adding.

When the product count is greater than `0`, adding more of that product increases the product count by the amount added, and the product price will be recalculated as the total value of all existing products plus the total value of all newly added products, divided by the new total product count, rounded up to the nearest integer.

```python
new_product_count: int = product_count + products_added
new_product_price: int = math.ceil((product_price * product_count + total_value_of_new_products_added) / new_product_count)
```

### When the product count is less than `0` before adding.

> [!NOTE]
> This situation can happen when the product count in the system does not accurately reflect the real-world stock of that product.
> This sometimes happens when people throw away product that have gone bad, or if someone buys something and forgets to actually take it from the shelf.

When the product count is less than `0`, adding more of that product increases the product count by the amount added. The product price will be recalculated with an assumption that the existing negative stock has a total value of `0`, plus the total value of all newly added products.

> [!WARN]
> Note that this means that if you add products to a negative stock and the stock is still negative,
> the product price will be completely recalculated the next time someone adds the same product.
> There will also be a noticeable effect if the stock goes from negative to positive.

```python
new_product_count: int = product_count + products_added
new_product_price: int = math.ceil(((product_price * max(product_count, 0)) + (total_value_of_new_products_added)) / new_product_count)
```

### A note about adding `0` items

If a user attempts to add `0` items of a product, the system will not change the product count or price, and no transaction will be recorded.


## Buying products - product stock

### When the product count is positive and you buy less than or equal to the stock count

When the product count is positive and a user buys an amount less than or equal to the current stock count, the product stock count will be decreased by the amount bought.

```python
new_product_count: int = product_count - products_bought
```

### When the product count is positive or `0` and you buy more than there are in stock

When the product count is positive and a user buys an amount greater than the current stock count, the product stock count will be decreased by the amount bought, resulting in a negative stock count.

```python
new_product_count: int = product_count - products_bought
```

> [!NOTE]
> This should also yield a warning, recommending the user to adjust the stock count for the product in question.

### Buying from negative stock

When the product count is negative, buying more of that product will further decrease the product stock count.

```python
new_product_count: int = product_count - products_bought
```

> [!NOTE]
> This should also yield a warning, recommending the user to adjust the stock count for the product in question.

### Buying items with joint transactions.

The same rules as above apply for all 3 cases.

### Note about buying `0` items

If a user attempts to buy `0` items of a product, the system will not change the product count or price, and no transaction will be recorded.


## Interest and penalty

### What is interest, and why do we need it

We have had some issues with the economy going in the negative, most likely due to users throwing away products gone bad. When the economy goes negative, we end up in a situation where users have money but there aren't really any products to buy, because the users don't have the incentive to add products back into the system to gain more balance.

To readjust the economy over time, there is an interest rate that will increase the amount you pay for each product by a certain percentage (the interest rate). This percentage can be adjusted by administrators when they see that the economy needs fixing. By default, the interest rate is set to `100%` (i.e., you don't pay anything extra).

> [!NOTE]
> You can not go below `100%` interest rate.

### What is penalty, and why do we need it

We currently allow users to go into negative balance when buying products. This is useful when you're having a great time at hacking night or similar, and don't want to be stopped by a low balance. However, to avoid users going too deep into negative balance, we make the cost of the product multiply by a penalty multiplier once the user's balance goes below a certain threshold. This penalty multiplier and threshold can be adjusted by administrators. By default, the threshold is set to `-100` krs, and the penalty multiplier is set to `200%` (i.e. you pay double the amount of money for products once your balance goes below `-100` krs).

The penalty starts counting as soon as your balance goes below the threshold, not when it is equal to the threshold.

> [!NOTE]
> You can not set the penalty multiplier to below `100%` (that would be a rebate, not a penalty),
> and you can not set the penalty threshold to above `0` krs (we do not punish people for having money).

## Adding products - user balance

### When your existing balance is above the penalty threshold

You gain balance equal to the total value of the products you add.

Note that this might be separate from the per-product cost of the products after you add them, due to rounding and price recalculation.

```python
new_user_balance: int = user_balance + total_value_of_products_added

assert total_value_of_new_products_added >= product_price * products_added
```

### When your existing balance is below the penalty threshold

This case is the same as above.


## Buying products - user balance

### When your existing balance is above the penalty threshold, and the purchase does not push you below the threshold

You pay the normal product price for the products you buy, plus any interest.

```python
new_user_balance: int = user_balance - math.ceil(products_bought * product_price * (interest_rate / 100))
```

Note that the system performs a transaction for every product kind, so if you buy multiple different products in one go, the rounding is done per product kind.

### When your balance is below the penalty threshold before buying

You pay the penalized product price for the products you buy, plus any interest.

The interest and penalty are calculated separately before they are added together, *not* multiplied together.

```python
base_cost: float = product_price * products_bought
penalty: float = (base_cost * (penalty_multiplier / 100)) - base_cost
interest: float = (base_cost * (interest_rate / 100)) - base_cost
new_user_balance: int = user_balance - math.ceil(base_cost + penalty + interest)
```

### When your balance is above the penalty threshold before buying, but the purchase pushes you below the threshold

When your balance is above the penalty threshold before buying, but the purchase pushes you below the threshold, the system not apply any penalty for the purchase. The entire purchase is done at the normal product price plus any interest.

```python
new_user_balance: int = user_balance - math.ceil(products_bought * product_price * (interest_rate / 100))
```

> [!NOTE]
> In the case where you are performing multiple transactions at once, the system should try its best to order the purchases in a way that minimizes the amount of penalties you need to pay.

### Joint purchases, when all users are above the penalty threshold and stays above the threshold

When making joint purchases (multiple users buying products together), and all users are above the penalty threshold before and after the purchase, the total cost (including interest) will be split equally between all users. The price will be rounded up for each user after splitting the bill.

```python
total_cost: float = product_price * products_bought * (interest_rate / 100)
cost_per_user: float = total_cost / number_of_users
new_user_balance = user_balance - math.ceil(cost_per_user)
```

### Joint purchases where a user appears more than one time

When a user appears more than once in a joint purchase (e.g. two people buying together, but one of them is buying twice as much as the other), the system will the amount of times a user appears in the purchase as a multiplier for the base price. You can think of it as if the user is having shares in the joint purchase.

```python
base_cost_for_user: float = product_price * products_bought * user_shares / total_user_shares
added_interest: float = base_cost_for_user * ((interest_rate - 100) / 100)
new_user_balance: int = user_balance - math.ceil(base_cost_for_user + added_interest)
```

### Joint purchases when one or more users are below the penalty threshold

The cost for each user will be calculated as usual, but for the users who are below the penalty threshold, the penalty will also be calculated and added to this user's cost. The penalty is calculated based on the share of the total purchase that this user is responsible for.


```python
base_cost_for_user: float = product_price * products_bought * user_shares / total_user_shares
added_interest: float = base_cost_for_user * ((interest_rate - 100) / 100)
penalty: float = base_cost_for_user * ((penalty_multiplier - 100) / 100)
new_user_balance: int = user_balance - math.ceil(base_cost_for_user + added_interest + penalty)
```

### Joint purchases when one or more users will end up below the penalty threshold after the purchase

Just as the single-user case, if a user who is part of a joint purchase is above the penalty threshold before the purchase, but will end up below the threshold after the purchase, no penalty will be applied to that user for this purchase. The entire cost (including interest) will be split equally between all users.

```python
base_cost_for_user: float = product_price * products_bought * user_shares / total_user_shares
added_interest: float = base_cost_for_user * ((interest_rate - 100) / 100)
new_user_balance: int = user_balance - math.ceil(base_cost_for_user + added_interest)
```

> [!NOTE]
> In the case where you (and others) are performing multiple transactions at once, the system should try its best to order the purchases in a way that minimizes the amount of penalties you need to pay.

## Who owns a product

When throwing away products, it can be useful to know who added the products in the first place. Dibbler will look back at its event log to determine who added the products that are being thrown away, and pull the money from their balance in order for the economy to stay sane.

The algorithm is based on FIFO (first in, first out), meaning that the products that were added first are the ones that will be considered thrown away first. This might not always be accurate in real life (someone could buy a newer product and add it to the shelf before an older product is added and then considered newer by the system), but it is an overall reasonable approximation.

When adjusting the product count upwards manually, the system will consider the new products to not be owned by anyone. When adjusting the product count downwards manually, the system will let go of ownership of the products being removed according to the FIFO queue, without adjusting their balance.

If the stock count of a product goes negative, the system will consider that the products being bought are owned by no one, and will not adjust any balances. The system should warn about the negative stock count, and recommend recounting the stock. As mentioned above, the manual adjustment made when recounting the stock will not assign ownership to anyone.

Upon throwing away products (not manual adjustment), the system will pull money from the balances of the users who added the products being thrown away, according to the FIFO queue. In the case where the systemd decides that no one own the products due to manual adjustments, the system will not pull any money from anyone's balance and let the economy absorb the loss.

## Other actions

### Transfers

You can transfer money from one user to another. The amount transferred will be deducted from the sender's balance and added to the receiver's balance without any interest or penalty applied.

```python
new_sender_balance: int = sender_balance - amount_transferred
new_receiver_balance: int = receiver_balance + amount_transferred
```

> [!NOTE]
> Transfers from one user to itself are not allowed.

### Balance adjustments

You can manually adjust a user's balance. This action will not have any multipliers of any kind applied, and will simply add or subtract the specified amount from the user's balance.

```python
new_user_balance: int = user_balance + adjustment_amount
```

## Updating the economy specification

All transactions in the database are tagged with the economy specification version they were created under. If you are to update this document with changes to how the economy works, and change the software accordingly, you will want to keep the old logic around and bump the version number. This way, the old event log is still valid, and will be aggregated using the old logic, while new transactions will user the logic applicable to the version they were created under.
