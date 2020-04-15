<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
| Here is where you can register API routes for your application. These
| routes are loaded by the RouteServiceProvider within a group which
| is assigned the "api" middleware group. Enjoy building your API!
|
 */
/*
    /hr/HRMaster/replicate
Route::get('hr/HRMaster/replicate', 'ApisADController@show');

Route::put('/replicate', 'ApisADController@update');
Route::middleware('auth:api')->get('/replicate', 'ApisADController@show');
 */
/*
Route::get('/replicate', 'ApisADController@show');
 */
Route::group(['middleware'=>'auth:api'], function(){
    /* Route::put('/replicate', 'ApisADController@update'); 
    Route::get('/replicate', 'ApisADController@list'); */
    Route::put('/hr/HRMaster/replicate', 'ApisADController@update');
    Route::get('/hr/HRMaster/replicate', 'ApisADController@list'); 
  /* Route::get('/user', function (Request $request) {
    return $request->user();
  }); */
});
