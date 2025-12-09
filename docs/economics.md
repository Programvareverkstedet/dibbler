# Economics

This document provides an overview of how dibbler counts and calculates its running event log.

It is a sort of semi-formal specification for how dibbler's economy is intended to work, and is useful for both users and developers to understand the underlying mechanics.

## Some general notes

- All calculations involving money are done in whole numbers (integers). There are no fractional krs.
- All rounding is done by rounding up to the nearest integer, in favor of the system economy - not the users.

## Adding products - product stock and product price

This section covers what happens to the stock count and price of a product when a user adds more of that product to the system.

### When the product count is `0` before adding.

When the product count is `0`, adding more of that product sets the product count to the amount added, and the product price will be set to the price of all products added divided by the number of products added, rounded up to the nearest integer.

```python
new_product_count = products_added
new_product_price = math.ceil(total_value_of_products_added / products_added)
```

### When the product count is greater than `0` before adding.

When the product count is greater than `0`, adding more of that product increases the product count by the amount added, and the product price will be recalculated as the total value of all existing products plus the total value of all newly added products, divided by the new total product count, rounded up to the nearest integer.

```python
new_product_count = product_count + products_added
new_product_price = math.ceil((total_value_of_existing_products + total_value_of_products_added) / new_product_count)
```

### When the product count is less than `0` before adding.

> [!NOTE]
> This situation can happen when the product count in the system does not accurately reflect the real-world stock of that product.
> This sometimes happens when people throw away product that have gone bad, or if someone buys something and forgets to actually take it from the shelf.

When the product count is less than `0`, adding more of that product increases the product count by the amount added. The product price will be recalculated with an assumption that the existing negative stock has a total value of `0`, plus the total value of all newly added products.

Note that this means that if you add products to a negative stock and the stock is still negative, the product price will be completely recalculated the next time someone adds the same product. There will also be a noticable effect if the stock goes from negative to positive.

```python
new_product_count = product_count + products_added
new_product_price = math.ceil(((product_price * math.max(product_count, 0)) + (total_value_of_products_added)) / new_product_count)
```

### A note about adding `0` items

If a user attempts to add `0` items of a product, the system will not change the product count or price, and no transaction will be recorded.


## Buying products - product stock

### When the product count is positive and you buy less than or equal to the stock count

When the product count is positive and a user buys an amount less than or equal to the current stock count, the product stock count will be decreased by the amount bought.

```python
new_product_count = product_count - products_bought
```

### When the product count is positive or `0` and you buy more than there are in stock

When the product count is positive and a user buys an amount greater than the current stock count, the product stock count will be decreased by the amount bought, resulting in a negative stock count.

```python
new_product_count = product_count - products_bought
```

This should also yield a warning, recommending the user to adjust the stock count for the product in question.

### Buying from negative stock

When the product count is negative, buying more of that product will further decrease the product stock count.

```python
new_product_count = product_count - products_bought
```

This should also yield a warning, recommending the user to adjust the stock count for the product in question.

### Buying items with joint transactions.

The same rules as above apply for all 3 cases.

### Note about buying `0` items

If a user attempts to buy `0` items of a product, the system will not change the product count or price, and no transaction will be recorded.


## Interest and penalty

### What is interest, and why do we need it

We have had some issues with the economy going in the negative, most likely due to users throwing away products gone bad. When the economy goes negative, we end up in a situation where users have money but there aren't really any products to buy, because the users don't have the incentive to add products back into the system to gain more balance.

To readjust the economy over time, there is an interest rate that will increase the amount you pay for each product by a certain percentage (the interest rate). This percentage can be adjusted by administrators when they see that the economy needs fixing. By default, the interest rate is set to `0%`.

You can not go below `0%` interest rate.

### What is penalty, and why do we need it

We currently allow users to go into negative balance when buying products. This is useful when you're having a great time at hacking night or similar, and don't want to be stopped by a low balance. However, to avoid users going too deep into negative balance, we make the cost of the product multiply by a penalty multiplier once the user's balance goes below a certain threshold. This penalty multiplier and threshold can be adjusted by administrators. By default, the threshold is set to `-100` krs, and the penalty multiplier is set to `200%` (i.e. you pay double the amount of money for products once your balance goes below `-100` krs).

You can not set the penalty multiplier to below `100%` (that would be a rebate, not a penalty), and you can not set the penalty threshold to above `0` krs (we do not punish people for having money).


## Adding products - user balance

### When your existing balance is above the penalty threshold

You gain balance equal to the total value of the products you add.

Note that this might be separate from the per-product cost of the products after you add them, due to rounding and price recalculation.

```python
new_user_balance = user_balance + total_value_of_products_added
```

### When your existing balance is below the penalty threshold

This case is the same as above.


## Buying products - user balance

### When your existing balance is above the penalty threshold, and the purchase does not push you below the threshold

You pay the normal product price for the products you buy, plus any interest.

```python
new_user_balance = user_balance - (products_bought * product_price * (1 + interest_rate))
```

Note that the system performs a transaction for every product kind, so if you buy multiple different products in one go, the rounding is done per product kind.

### When your balance is below the penalty threshold before buying

You pay the penalized product price for the products you buy, plus any interest.

The interest and penalty are calculated separately before they are added together, *not* multiplied together.

```python
penalty = ((product_price * penalty_multiplier) - product_price)
interest = (product_price * interest_rate)
new_user_balance = user_balance - (products_bought * (product_price + penalty + interest))
```

### When your balance is above the penalty threshold before buying, but the purchase pushes you below the threshold

TODO:

```python
```

### Joint purchases, when all users are above the penalty threshold and stays above the threshold

TODO: how does rounding work here, does one user pay more than the other?

TODO: ordering the purchases in favor of the user.

When performing joing purchases (multiple users


### Joint purchases when one or more users are below the penalty threshold

TODO

### Joint purchases when one or more users will end up below the penalty threshold after the purchase

TODO

## Who owns a product

When throwing away products, it can be useful to know who added the products in the first place. Dibbler will look back at its event log to determine who added the products that are being thrown away, and pull the money from their balance in order for the economy to stay sane.

The algorithm is based on FIFO (first in, first out), meaning that the products that were added first are the ones that will be considered thrown away first. This might not always be accurate in real life (someone could buy a newer product and add it to the shelf before an older product is added and then considered newer by the system), but it is an overall reasonable approximation.

### When adding a product

### When buying a product

### When adjusting the product count

## Other actions

Transfers

  Note about self-transfers

Balance adjustments

## Updating the economy specification

Keep old logic, database rows tagged with spec version.
